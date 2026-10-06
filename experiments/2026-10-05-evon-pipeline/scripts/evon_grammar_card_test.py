"""Can Evon use the Grammar-40 pilot's 8x5 learning to name the language variety?

Turns the pilot's top-5 parameters per language (data/grammar40_pilot/results.json, 8 languages) into a plain-text
"grammar card", then asks Evon to name the variety of each test transcript in two arms:

  A: no card  -- the question alone (baseline: what Evon already knows)
  B: card     -- the same question with the 8x5 card included

The prompts are identical apart from the card, so B minus A is the card's contribution. Test transcripts are written
by hand in a JSONL file, one object per line:

  {"id": "bho-01", "transcript": "...", "expected": "Bhojpuri", "context": "optional", "note": "optional"}

Without "context", Evon is only asked to name the variety. With "context" (a role and situation), Evon is asked to
reply in that role in the caller's own language, and to state first which variety it heard, so the reply can be read
and the variety scored in the same call.

`expected` must be one of the 8 pilot languages. Ideally the transcripts are Prisma output (what Evon sees in
production) and NOT taken from the pilot's 999-clip manifest, which the card was learned from.

Usage:
  python evon_grammar_card_test.py --write-card              # write the card text for review, no Evon calls
  python evon_grammar_card_test.py --tests T.jsonl --dry-run # print one full prompt, no Evon calls
  python evon_grammar_card_test.py --tests T.jsonl           # run both arms (2 Evon calls per test)

Evon is reached at BOLI_EVON_URL (default: the deployed Modal endpoint) with BOLI_EVON_MODEL. Each call costs Modal
GPU time, and the first call after an idle period can take minutes while the A100 cold-boots.
"""

import argparse
import json
import os
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import httpx

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "grammar40_pilot"
RESULTS_PATH = DATA_DIR / "results.json"
CARD_PATH = DATA_DIR / "evon_card_8x5.txt"

EVON_URL = os.environ.get("BOLI_EVON_URL", "https://sameer261h--evon-v3-3-serve-serve.modal.run").rstrip("/")
EVON_MODEL = os.environ.get("BOLI_EVON_MODEL", "/weights/gnani/gnani-evon-v3.3-30B-A3B")

LANGS = ["Hindi", "Bhojpuri", "Maithili", "Chhattisgarhi", "Rajasthani", "Garhwali", "Khariboli", "Kumaoni"]
# Same family grouping the pilot used (METHOD.md), for family-level scoring only.
FAMILY = {"Bhojpuri": "Bihari", "Maithili": "Bihari", "Chhattisgarhi": "Eastern-Hindi", "Rajasthani": "Rajasthani",
          "Garhwali": "Pahari", "Kumaoni": "Pahari", "Hindi": "Western-Hindi", "Khariboli": "Western-Hindi"}
# Evon sometimes answers in Devanagari.
ALIASES = {"हिंदी": "Hindi", "हिन्दी": "Hindi", "भोजपुरी": "Bhojpuri", "मैथिली": "Maithili",
           "छत्तीसगढ़ी": "Chhattisgarhi", "छत्तीसगढी": "Chhattisgarhi", "राजस्थानी": "Rajasthani",
           "गढ़वाली": "Garhwali", "गढवाली": "Garhwali", "खड़ीबोली": "Khariboli", "खड़ी बोली": "Khariboli",
           "खडी बोली": "Khariboli", "कुमाऊँनी": "Kumaoni", "कुमाउनी": "Kumaoni", "कुमांऊनी": "Kumaoni"}

QUESTION = """Below is one turn of a phone caller's speech, as transcribed by a Hindi speech recogniser. Because the \
recogniser works in Hindi, some regional words may have been rewritten into Hindi spellings.

Transcript:
{transcript}
{card}
Which of these language varieties is the caller most likely speaking: {langs}?

Answer in exactly this format, on two lines:
LANGUAGE: <one name from the list>
EVIDENCE: <the words in the transcript that led you there, or "none">"""

ROLE_PROMPT = """{context}

Below is the other person's last turn in an ongoing conversation, as transcribed by a Hindi speech recogniser. \
Because the recogniser works in Hindi, some regional words may have been rewritten into Hindi spellings.

Their turn:
{transcript}
{card}
Understand what they said and reply naturally in the same language they used. Do not describe, translate, or \
summarise their speech. Respond directly to them as that person would in this situation.

Answer in exactly this format, on two lines:
LANGUAGE: <the variety they are speaking, one of: {langs}>
REPLY: <your reply to them>"""

CARD_INTRO = """
Notes on how each variety tends to show up in transcripts like this one, learned from about 125 transcripts per \
variety. For each variety, the five grammar features that best separated it from the others. "more often here" \
lists forms at least twice as frequent in that variety as in the others; "less often here" lists forms at most half \
as frequent. Forms used about equally everywhere are left out.
"""
MARKER_RE = re.compile(r"^(.+?) \[(\d+) in .+? / (\d+) elsewhere\]$")


def build_card(top_k=5):
    data = json.loads(RESULTS_PATH.read_text())
    langs, n_total = data["languages"], data["n_rows"]
    lines = [CARD_INTRO]
    for lang in LANGS:
        n_here = langs[lang]["n_clips"]
        params = sorted(langs[lang]["parameters"], key=lambda q: -(q["exact_language_score"] or 0))[:top_k]
        lines.append(f"{lang}:")
        for i, q in enumerate(params, 1):
            # The pilot's present/absent flag is about the whole feature class; each listed form carries its own
            # counts, which can point the other way (Garhwali's class is absent-driven, yet छ/छन are Garhwali forms).
            more, less = [], []
            for m in q["observed_markers"]:
                form, here, elsewhere = MARKER_RE.match(m).groups()
                ratio = (int(here) / n_here) / max(int(elsewhere) / (n_total - n_here), 1e-9)
                (more if ratio >= 2 else less if ratio <= 0.5 else []).append(form)
            absent = "absent-driven" in q["notes"]
            parts = [f"appears {'less' if absent else 'more'} often here than in the other varieties"]
            if more:
                parts.append("more often here: " + ", ".join(more))
            if less:
                parts.append("less often here: " + ", ".join(less))
            lines.append(f"  {i}. {q['name']}: " + "; ".join(parts))
    return "\n".join(lines) + "\n"


def make_prompt(test, card):
    template = ROLE_PROMPT if test.get("context") else QUESTION
    return template.format(transcript=test["transcript"], card=card, langs=", ".join(LANGS), context=test.get("context"))


def parse_reply(raw):
    answer = raw.rsplit("</think>", 1)[-1]
    match = re.search(r"REPLY\s*:\s*(.+)", answer, re.IGNORECASE | re.DOTALL)
    return match.group(1).strip() if match else None


def parse_language(raw):
    answer = raw.rsplit("</think>", 1)[-1]
    match = re.search(r"LANGUAGE\s*:\s*(.+)", answer, re.IGNORECASE)
    text = (match.group(1) if match else answer).strip()
    for lang in LANGS:
        if lang.lower() in text.lower():
            return lang
    for alias, lang in ALIASES.items():
        if alias in text:
            return lang
    return "UNPARSED"


def call_evon(client, content):
    started = time.time()
    resp = client.post(f"{EVON_URL}/v1/chat/completions", json={
        "model": EVON_MODEL, "messages": [{"role": "user", "content": content}],
        "temperature": 0, "max_tokens": 4096,
    })
    resp.raise_for_status()
    body = resp.json()
    choice = body["choices"][0]
    return {"raw_output": choice["message"]["content"], "finish_reason": choice["finish_reason"],
            "usage": body.get("usage"), "latency_sec": round(time.time() - started, 2)}


def load_tests(path):
    tests = []
    for n, line in enumerate(Path(path).read_text().splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("//"):
            continue
        t = json.loads(line)
        if t.get("expected") not in LANGS:
            sys.exit(f"line {n}: expected must be one of {LANGS}, got {t.get('expected')!r}")
        t.setdefault("id", f"line{n}")
        tests.append(t)
    return tests


def summarise(rows, arms):
    out = ["| Arm | Exact correct | Family correct | Unparsed | Hit max_tokens |", "|---|---|---|---|---|"]
    for arm in arms:
        r = [x for x in rows if x["arm"] == arm]
        exact = sum(x["predicted"] == x["expected"] for x in r)
        fam = sum(FAMILY.get(x["predicted"]) == FAMILY[x["expected"]] for x in r)
        out.append(f"| {arm} | {exact}/{len(r)} ({100 * exact / len(r):.0f}%) | {fam}/{len(r)} ({100 * fam / len(r):.0f}%) "
                   f"| {sum(x['predicted'] == 'UNPARSED' for x in r)} | {sum(x['finish_reason'] == 'length' for x in r)} |")
    out += ["", "Per expected language (exact correct):", "",
            "| Expected | n | " + " | ".join(arms) + " |", "|---|---|" + "---|" * len(arms)]
    for lang in LANGS:
        r = [x for x in rows if x["expected"] == lang]
        if r:
            n = len(r) // len(arms)
            out.append(f"| {lang} | {n} | " + " | ".join(
                f"{sum(x['predicted'] == lang for x in r if x['arm'] == a)}/{n}" for a in arms) + " |")
    out += ["", "Predictions (expected -> predicted counts):", ""]
    for arm in arms:
        conf = defaultdict(Counter)
        for x in rows:
            if x["arm"] == arm:
                conf[x["expected"]][x["predicted"]] += 1
        out.append(f"- **{arm}**: " + "; ".join(
            f"{e} -> " + ", ".join(f"{p} {c}" for p, c in conf[e].most_common()) for e in LANGS if e in conf))
    flips = [(x["id"], x["expected"]) for x in rows if x["arm"] == "B_card"
             and any(y["id"] == x["id"] and y["arm"] == "A_no_card" and (y["predicted"] == y["expected"]) != (x["predicted"] == x["expected"]) for y in rows)]
    if flips:
        out += ["", "Tests where the card changed the outcome: " + ", ".join(f"{i} ({e})" for i, e in flips)]
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--tests", help="JSONL file of hand-written test cases")
    ap.add_argument("--arms", default="A_no_card,B_card", help="comma-separated: A_no_card, B_card")
    ap.add_argument("--write-card", action="store_true", help=f"write the card to {CARD_PATH.name} and exit")
    ap.add_argument("--only", help="comma-separated test ids to run (default: all)")
    ap.add_argument("--dry-run", action="store_true", help="print the first test's card prompt, make no Evon calls")
    args = ap.parse_args()

    card = build_card()
    if args.write_card:
        CARD_PATH.write_text(card)
        print(f"Wrote {CARD_PATH}")
        return
    if not args.tests:
        ap.error("--tests is required unless --write-card is given")
    tests = load_tests(args.tests)
    if args.only:
        tests = [t for t in tests if t["id"] in args.only.split(",")]
    arms = [a.strip() for a in args.arms.split(",")]
    if args.dry_run:
        print(make_prompt(tests[0], card if "B_card" in arms else ""))
        print(f"\n[dry run] {len(tests)} tests x {len(arms)} arms = {len(tests) * len(arms)} Evon calls would be made.")
        return

    out_path = Path(args.tests).with_suffix(f".{args.only.replace(',', '_')}.results.json" if args.only else ".results.json")
    rows = []
    with httpx.Client(timeout=httpx.Timeout(600, connect=10), follow_redirects=True) as client:
        for t in tests:
            for arm in arms:
                prompt = make_prompt(t, card if arm == "B_card" else "")
                res = call_evon(client, prompt)
                row = {**t, "arm": arm, "prompt": prompt, **res, "predicted": parse_language(res["raw_output"]),
                       "reply": parse_reply(res["raw_output"])}
                rows.append(row)
                print(f"{t['id']:>12} {arm:10} expected={t['expected']:13} predicted={row['predicted']:13} "
                      f"{'OK' if row['predicted'] == t['expected'] else '--'}  {res['latency_sec']}s")
                if row["reply"]:
                    print(f"{'':>12} reply: {row['reply']}")
                out_path.write_text(json.dumps(rows, ensure_ascii=False, indent=1))  # save as we go
    summary = summarise(rows, arms)
    out_path.with_suffix(".summary.md").write_text(summary + "\n")
    print("\n" + summary + f"\n\nFull outputs: {out_path}")


if __name__ == "__main__":
    main()
