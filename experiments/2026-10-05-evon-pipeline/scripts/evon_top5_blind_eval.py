"""Blinded test: does teaching Evon the Grammar-40 Top-5 markers per language help it name the language from Prisma text?

Stages (each a subcommand), run in order:

  table    print the 8 x Top-5 marker table and its source file
  prompt   write the teaching prompt (generated only from the pilot's results.json) to TEACHING_PROMPT_PATH
  items    build the blinded eval set: items_blind.jsonl (opaque id + Prisma transcript only) and, in a separate
           file, gold_key.jsonl. Runs the leakage controls and refuses to write anything if one fails.
  infer    call Evon on items_blind.jsonl only; saves predictions_<arm>.jsonl. Never opens the gold key.
           --arm taught: the teaching prompt is included. --arm untaught: the same item prompt without it (control).
  score    join predictions with the gold key and report (only after infer has finished every item of the arm)

Hindi: the 130a39d manifest has no Hindi Prisma transcripts, and the pilot's Hindi clips are its training data, so
by the user's decision the eval covers the other 7 languages while Hindi stays one of the 8 possible answers.

Eval rows come from the 1,000-clip manifest frozen at commit 130a39d (shared_1k_audio_manifest.jsonl on branch
claude/determined-brahmagupta-ro0jiw), minus every row in the 999-clip manifest the Grammar-40 pilot learned its
rankings from (commit df83a25). The Top-5 rankings come from data/grammar40_pilot/results.json (pilot commit 654f6e2).
"""

import argparse
import json
import random
import re
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
RESULTS_PATH = ROOT / "data" / "grammar40_pilot" / "results.json"
OUT_DIR = ROOT / "data" / "grammar40_pilot" / "top5_blind_eval"
TEACHING_PROMPT_PATH = OUT_DIR / "teaching_prompt.txt"

LANGS = ["Hindi", "Bhojpuri", "Maithili", "Chhattisgarhi", "Rajasthani", "Garhwali", "Khariboli", "Kumaoni"]
CODES = {"Hindi": "HIN", "Bhojpuri": "BHO", "Maithili": "MAI", "Chhattisgarhi": "CHH", "Rajasthani": "RAJ",
         "Garhwali": "GAR", "Khariboli": "KHA", "Kumaoni": "KUM"}
NAME_PATTERNS = {  # gold-name leakage check on everything item-specific that Evon sees
    "Hindi": r"hindi|हिंदी|हिन्दी", "Bhojpuri": r"bhojpuri|भोजपुरी", "Maithili": r"maithili|मैथिली",
    "Chhattisgarhi": r"chhattisgarh|छत्तीसगढ", "Rajasthani": r"rajasthan|राजस्थान", "Garhwali": r"garhwal|गढ़वाल|गढवाल",
    "Khariboli": r"khari ?boli|खड़ी ?बोली|खडी ?बोली", "Kumaoni": r"kumaon|कुमाऊ|कुमाउ"}

# Language-independent definitions of the 16 Grammar-40 classes that occur in any Top-5. Written once from the class
# names; no evaluation transcript was consulted.
GLOSSARY = {
    "Copulas": "forms of 'to be' that link a subject to a description (Hindi है, हैं)",
    "Non-copular auxiliaries": "helper verbs after a main verb that mark ongoing or continuing action (Hindi रहा, रही, रहे)",
    "Tense morphology": "verb endings that mark past, present or future",
    "Aspect morphology": "verb endings that mark whether an action is habitual, ongoing or completed",
    "Gender agreement": "verb and adjective endings that change with the gender of the subject (Hindi बैठा vs बैठी)",
    "Participles / converbs": "verb forms used like adjectives or to join actions (Hindi बना हुआ, करके)",
    "Basic pronouns": "I, we, you, he, she, they",
    "Demonstratives": "this, that, these, those",
    "Interrogatives": "question words: what, how much, where, who",
    "Indefinite / quantifier paradigms": "words for some, all, every, any, each",
    "Case / postposition system": "small words after a noun marking its role: of, to, from, in, on, for",
    "Numeral classifiers / count markers": "a small word attached to a number when counting things",
    "Locative / deictic adverbs": "words for where something is: here, there, in front, behind, inside, outside",
    "Conjunctions": "joining words: and, or, but",
    "Vocative / address particles": "words used when addressing or calling someone",
    "Comparative / degree markers": "words for how much: very, quite, more",
}
MARKER_RE = re.compile(r"^(.+?) \[(\d+) in .+? / (\d+) elsewhere\]$")

ENDING = ("You may receive speech transcribed imperfectly by Prisma. Use the grammatical evidence above to infer which "
          "of these languages is most likely being spoken. Do not assume every marker will survive ASR. Base your "
          "judgment on the strongest surviving evidence. Then respond naturally in the language you believe the "
          "speaker used.")
CONTEXT = ("You are a relative on a call. The other person is describing what they can see around them. Understand what "
           "they said and reply naturally in the same language they used. Do not translate or summarize.")
OUTPUT_SPEC = """Return exactly one JSON object and nothing else:
{
  "predicted_language": "<one of: %s>",
  "confidence": <0.00 to 1.00>,
  "matched_markers": [{"marker": "<marker code, e.g. BHO-1>", "evidence": "<exact short span copied from the transcript>"}],
  "reason": "<one short sentence explaining the grammatical evidence>",
  "reply": "<natural reply to the speaker in the predicted language>"
}
Rules: list a marker only if it is one of the coded markers taught above AND you can copy its evidence exactly from \
the transcript. Never invent evidence. Markers whose clue is that a form is rarer can only be cited with a span that \
shows the rarer-form pattern; otherwise leave them out. If no taught marker survives in the transcript, return an \
empty list. Confidence must reflect how strong the surviving evidence is, not the fact that you must pick one of \
the %d languages.""" % (", ".join(LANGS), len(LANGS))


def top5():
    data = json.loads(RESULTS_PATH.read_text())
    out = {}
    for lang in LANGS:
        v = data["languages"][lang]
        params = sorted(v["parameters"], key=lambda q: -(q["exact_language_score"] or 0))[:5]
        out[lang] = (v["n_clips"], data["n_rows"], params)
    return out


def teaching_prompt():
    lines = ["You will help identify which of 8 related Indian language varieties a speaker is using. Below, for each "
             "variety, are the 5 grammatical markers that best told it apart from the other 7 in an earlier analysis "
             "of speech-recogniser transcripts. Each marker has a code. \"More common here\" lists forms at least "
             "twice as frequent in that variety as in the others; \"rarer here\" lists forms at most half as frequent. "
             "Some markers are clues by absence: the variety uses that kind of form less than the others do.", ""]
    for lang, (n_here, n_total, params) in top5().items():
        lines.append(f"{lang}")
        for i, q in enumerate(params, 1):
            more, less = [], []
            for m in q["observed_markers"]:
                form, here, elsewhere = MARKER_RE.match(m).groups()
                ratio = (int(here) / n_here) / max(int(elsewhere) / (n_total - n_here), 1e-9)
                (more if ratio >= 2 else less if ratio <= 0.5 else []).append(form)
            absent = "absent-driven" in q["notes"]
            line = (f"  {CODES[lang]}-{i} {q['name']} ({GLOSSARY[q['name']]}). "
                    f"{'Clue by absence: used less here than in the others.' if absent else 'Used more here than in the others.'}")
            if more:
                line += " More common here: " + ", ".join(more) + "."
            if less:
                line += " Rarer here: " + ", ".join(less) + "."
            lines.append(line)
        lines.append("")
    lines.append(ENDING)
    return "\n".join(lines)


UNTAUGHT_INTRO = ("You will help identify which of 8 related Indian language varieties a speaker is using: %s.\n\n"
                  "You may receive speech transcribed imperfectly by Prisma. Infer which of these languages is most likely "
                  "being spoken. Base your judgment on the strongest surviving evidence. Then respond naturally in the "
                  "language you believe the speaker used." % ", ".join(LANGS))
UNTAUGHT_MARKER_RULE = ("\nNo marker set has been taught in this task, so always return \"matched_markers\": []. "
                        "Confidence must reflect how strong the evidence is, not the fact that you must pick one of the "
                        "%d languages." % len(LANGS))


def item_prompt(teaching, transcript):
    if teaching is None:  # untaught control: same context, transcript and JSON format, no teaching block
        spec = OUTPUT_SPEC.split("Rules:")[0].rstrip() + UNTAUGHT_MARKER_RULE
        return f"{UNTAUGHT_INTRO}\n\n{CONTEXT}\n\nPrisma transcript of their turn:\n{transcript}\n\n{spec}"
    return f"{teaching}\n\n{CONTEXT}\n\nPrisma transcript of their turn:\n{transcript}\n\n{OUTPUT_SPEC}"


def cmd_table(_):
    print(f"Source: {RESULTS_PATH.relative_to(ROOT.parent.parent)} (Grammar-40 pilot, commit 654f6e2), "
          "ranked by exact_language_score\n")
    print("| Language | Marker 1 | Marker 2 | Marker 3 | Marker 4 | Marker 5 |\n|---|---|---|---|---|---|")
    for lang, (_, _, params) in top5().items():
        print(f"| {lang} | " + " | ".join(q["name"] for q in params) + " |")


def cmd_prompt(_):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    TEACHING_PROMPT_PATH.write_text(teaching_prompt() + "\n")
    print(TEACHING_PROMPT_PATH.read_text())


def cmd_items(args):
    eval_rows = [json.loads(l) for l in open(args.eval_manifest)]
    train_rows = [json.loads(l) for l in open(args.train_manifest)]
    train_keys = {(r["shard"], r["row_idx"]) for r in train_rows}
    train_spk = {r["speaker_or_source_group"] for r in train_rows}
    train_txt = {r["prisma_transcript"] for r in train_rows}
    rows = [r for r in eval_rows if (r["shard"], r["row_idx"]) not in train_keys]
    failures = []
    per_lang = Counter(r["language"] for r in rows if r.get("prisma_transcript"))
    for lang in args.languages.split(","):
        if per_lang[lang] == 0:
            failures.append(f"{lang}: no eval rows with a Prisma transcript outside the pilot's training clips")
    if any(r["speaker_or_source_group"] in train_spk for r in rows):
        failures.append("an eval row shares a speaker key with the pilot's training clips")
    if any(r.get("prisma_transcript") in train_txt for r in rows if r.get("prisma_transcript")):
        failures.append("an eval transcript is identical to a pilot training transcript")
    for r in rows:
        if r.get("prisma_transcript") and re.search(NAME_PATTERNS[r["language"]], CONTEXT + r["prisma_transcript"], re.I):
            failures.append(f"gold language name appears in what Evon sees for {r['sample_id']}")
    if failures:
        print("LEAKAGE / DATA CONTROL FAILED -- nothing written:\n  " + "\n  ".join(failures))
        print("\nEval rows with Prisma, per language:", dict(per_lang))
        sys.exit(1)
    rows = [r for r in rows if r.get("prisma_transcript") and r["language"] in args.languages.split(",")]
    random.Random(20261006).shuffle(rows)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT_DIR / "items_blind.jsonl", "w") as blind, open(OUT_DIR / "gold_key.jsonl", "w") as gold:
        for r in rows:
            item_id = f"{random.Random(r['sample_id']).getrandbits(48):012x}"
            blind.write(json.dumps({"item_id": item_id, "transcript": r["prisma_transcript"]}, ensure_ascii=False) + "\n")
            gold.write(json.dumps({"item_id": item_id, "language": r["language"], "sample_id": r["sample_id"]}) + "\n")
    print(f"Wrote {len(rows)} blinded items. Per language: {dict(Counter(r['language'] for r in rows))}")


def parse_json(raw):
    text = raw.rsplit("</think>", 1)[-1]
    match = re.search(r"\{.*\}", text, re.DOTALL)
    try:
        return json.loads(match.group(0)) if match else None
    except json.JSONDecodeError:
        return None


def cmd_infer(args):
    teaching = TEACHING_PROMPT_PATH.read_text().rstrip("\n") if args.arm == "taught" else None
    items = [json.loads(l) for l in open(OUT_DIR / "items_blind.jsonl")][: args.n_items or None]
    pred_path = OUT_DIR / f"predictions_{args.arm}.jsonl"
    done = {json.loads(l)["item_id"] for l in open(pred_path)} if pred_path.exists() else set()
    todo = [it for it in items if it["item_id"] not in done][: args.limit or None]
    client = httpx.Client(timeout=httpx.Timeout(900, connect=10), follow_redirects=True)

    def run(it):
        started = time.time()
        resp = client.post(f"{args.evon_url.rstrip('/')}/v1/chat/completions", json={
            "model": args.evon_model, "temperature": 0, "max_tokens": 6000,
            "messages": [{"role": "user", "content": item_prompt(teaching, it["transcript"])}]})
        resp.raise_for_status()
        choice = resp.json()["choices"][0]
        raw = choice["message"]["content"]
        return {"item_id": it["item_id"], "transcript": it["transcript"], "raw_output": raw,
                "finish_reason": choice["finish_reason"], "parsed": parse_json(raw),
                "latency_sec": round(time.time() - started, 2)}

    from concurrent.futures import as_completed
    with ThreadPoolExecutor(args.workers) as pool, open(pred_path, "a") as out:
        for n, fut in enumerate(as_completed([pool.submit(run, it) for it in todo]), 1):
            rec = fut.result()
            out.write(json.dumps(rec, ensure_ascii=False) + "\n")
            out.flush()
            print(f"[{args.arm}] {n}/{len(todo)} {rec['item_id']} {rec['latency_sec']}s parsed={rec['parsed'] is not None}")


def cmd_score(args):
    print(f"## Arm: {args.arm}\n")
    items = [json.loads(l) for l in open(OUT_DIR / "items_blind.jsonl")][: args.n_items or None]
    keep = {it["item_id"] for it in items}
    preds = {p["item_id"]: p for p in map(json.loads, open(OUT_DIR / f"predictions_{args.arm}.jsonl")) if p["item_id"] in keep}
    missing = [it["item_id"] for it in items if it["item_id"] not in preds]
    if missing:
        sys.exit(f"{len(missing)} items have no saved prediction yet; finish infer before scoring.")
    gold = {g["item_id"]: g["language"] for g in map(json.loads, open(OUT_DIR / "gold_key.jsonl"))}
    taught = {f"{CODES[l]}-{i}" for l in LANGS for i in range(1, 6)}
    rows = []
    for item_id, p in preds.items():
        j = p["parsed"] or {}
        pred = j.get("predicted_language") if j.get("predicted_language") in LANGS else "UNPARSED"
        claimed = j.get("matched_markers") or []
        valid = [m for m in claimed if isinstance(m, dict) and str(m.get("marker", "")).upper() in taught
                 and m.get("evidence") and m["evidence"] in p["transcript"]]
        rows.append(dict(item_id=item_id, gold=gold[item_id], pred=pred, conf=j.get("confidence"), claimed=claimed,
                         n_valid=len({m["marker"].upper() for m in valid}), transcript=p["transcript"]))

    def acc(rs):
        return f"{sum(r['pred'] == r['gold'] for r in rs)}/{len(rs)} ({100 * sum(r['pred'] == r['gold'] for r in rs) / len(rs):.1f}%)" if rs else "n/a"

    print("| Language | N | Correct | Accuracy | ≥1 marker coverage |\n|---|---:|---:|---:|---:|")
    for lang in LANGS:
        rs = [r for r in rows if r["gold"] == lang]
        if not rs:
            print(f"| {lang} | 0 | - | - | - |")
            continue
        c = sum(r["pred"] == lang for r in rs)
        cov = sum(r["n_valid"] >= 1 for r in rs)
        print(f"| {lang} | {len(rs)} | {c} | {100 * c / len(rs):.1f}% | {100 * cov / len(rs):.1f}% |")
    print(f"\nOverall accuracy: {acc(rows)}")
    print(f"Unparsed outputs: {sum(r['pred'] == 'UNPARSED' for r in rows)}")
    print(f"≥1 valid marker: {sum(r['n_valid'] >= 1 for r in rows)} ({100 * sum(r['n_valid'] >= 1 for r in rows) / len(rows):.1f}%); "
          f"none: {sum(r['n_valid'] == 0 for r in rows)}")
    print(f"Accuracy | ≥1 marker: {acc([r for r in rows if r['n_valid'] >= 1])}")
    print(f"Accuracy | ≥2 markers: {acc([r for r in rows if r['n_valid'] >= 2])}")
    print(f"Accuracy | 0 markers: {acc([r for r in rows if r['n_valid'] == 0])}")
    for ok in (True, False):
        cs = [r["conf"] for r in rows if (r["pred"] == r["gold"]) == ok and isinstance(r["conf"], (int, float))]
        print(f"Mean confidence ({'correct' if ok else 'incorrect'}): {sum(cs) / len(cs):.2f}" if cs else "n/a")
    cols = LANGS + ["UNPARSED"]
    print("\nConfusion (rows gold, columns predicted):\n| gold \\ pred | " + " | ".join(CODES.get(c, "UNP") for c in cols) + " |")
    print("|---|" + "---:|" * len(cols))
    for g in [g for g in LANGS if any(r["gold"] == g for r in rows)]:
        print(f"| {g} | " + " | ".join(str(sum(r['gold'] == g and r['pred'] == c for r in rows)) for c in cols) + " |")
    with open(OUT_DIR / f"wrong_predictions_{args.arm}.jsonl", "w") as f:
        for r in rows:
            if r["pred"] != r["gold"]:
                checks = [{**m, "occurs_in_transcript": bool(isinstance(m, dict) and m.get("evidence") and m["evidence"] in r["transcript"])}
                          for m in r["claimed"]]
                f.write(json.dumps({"gold": r["gold"], "pred": r["pred"], "transcript": r["transcript"],
                                    "claimed_markers": checks}, ensure_ascii=False) + "\n")
    print(f"\nEvery wrong prediction, with claimed-marker checks: {OUT_DIR / f'wrong_predictions_{args.arm}.jsonl'}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("table")
    sub.add_parser("prompt")
    p = sub.add_parser("items")
    p.add_argument("--eval-manifest", required=True, help="the 130a39d shared_1k_audio_manifest.jsonl")
    p.add_argument("--train-manifest", required=True, help="the pilot's 999-clip shared_1k_audio_manifest.jsonl (df83a25)")
    p.add_argument("--languages", default=",".join(LANGS), help="gold languages to evaluate (all 8 stay possible answers)")
    p = sub.add_parser("infer")
    p.add_argument("--evon-url", default="https://sameer261h--evon-v3-3-serve-serve.modal.run")
    p.add_argument("--evon-model", default="/weights/gnani/gnani-evon-v3.3-30B-A3B")
    p.add_argument("--arm", choices=["taught", "untaught"], required=True)
    p.add_argument("--workers", type=int, default=8)
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--n-items", type=int, default=0, help="use only the first N items of the shuffled set (0 = all)")
    p = sub.add_parser("score")
    p.add_argument("--arm", choices=["taught", "untaught"], required=True)
    p.add_argument("--n-items", type=int, default=0, help="score only the first N items of the shuffled set (0 = all)")
    args = ap.parse_args()
    {"table": cmd_table, "prompt": cmd_prompt, "items": cmd_items, "infer": cmd_infer, "score": cmd_score}[args.cmd](args)


if __name__ == "__main__":
    main()
