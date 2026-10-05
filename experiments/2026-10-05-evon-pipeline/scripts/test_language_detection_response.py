"""Test: can Evon detect the customer's language/dialect and respond in kind?

Samples real Prisma-transcribed inputs (what Evon actually sees in production,
not the human reference) across all 19 pulled dialects, plus hand-written
Hindi and English controls. Sends each to Evon with an explicit instruction
to detect the language and reply in the same one, then scores:

  1. self-reported LANGUAGE_DETECTED vs. ground truth (broad-family match,
     since prior work in this project found single-utterance dialect
     CLASSIFICATION from text doesn't work well for closely-related
     Bihari-family dialects -- so "said Hindi" for a Bhojpuri input is
     scored separately from "said something unrelated entirely")
  2. script-level match of the REPLY (Devanagari vs Latin) -- cheap, reliable
  3. whether the REPLY contains any of that dialect's known corpus-derived
     markers (from data/markers_v2.json), as an honest, non-LLM-judge proxy
     for actual dialect-appropriate reply content

Usage:
  python test_language_detection_response.py
"""

import json
import random
import re
import time
from pathlib import Path

import httpx

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "prisma_fingerprint"
MARKERS_PATH = DATA_DIR.parent / "markers_v2.json"
OUT_PATH = DATA_DIR.parent / "language_detection_response_results.json"

EVON_URL = "https://sameer261h--evon-v3-3-serve-serve.modal.run/v1/chat/completions"
EVON_MODEL = "/weights/gnani/gnani-evon-v3.3-30B-A3B"

DIALECTS = [
    "Jaipuri", "Haryanvi", "Awadhi", "Surjapuri", "Bundeli", "Surgujia",
    "Angika", "Sadri", "Bajjika", "Khariboli", "Khortha", "Magahi",
    "Kumaoni", "Marwari", "Garhwali", "Rajasthani", "Maithili",
    "Chhattisgarhi", "Bhojpuri",
]
SAMPLES_PER_DIALECT = 5

HINDI_CONTROLS = [
    "मेरा ऑर्डर अभी तक नहीं पहुंचा है।",
    "क्या आप मुझे रिफंड दे सकते हैं?",
    "मुझे अपना बिल समझ नहीं आया।",
    "मैं कल तक भुगतान कर दूंगा।",
    "यह सेवा बहुत अच्छी नहीं है।",
    "कृपया मेरा पता बदल दीजिए।",
    "मुझे इस प्रोडक्ट की जानकारी चाहिए।",
    "आपका कस्टमर सपोर्ट बहुत धीमा है।",
    "मैंने पहले ही शिकायत दर्ज की थी।",
    "क्या यह ऑफर अभी भी उपलब्ध है?",
]
ENGLISH_CONTROLS = [
    "My order hasn't arrived yet.",
    "Can you give me a refund?",
    "I didn't understand my bill.",
    "I will make the payment by tomorrow.",
    "This service isn't very good.",
    "Please update my address.",
    "I need more information about this product.",
    "Your customer support is very slow.",
    "I already filed a complaint about this.",
    "Is this offer still available?",
]

TASK_TEMPLATE = """You are the reasoning engine for a customer-service voice agent in India.

The customer said:

{transcript}

Identify which language or regional dialect the customer is most likely speaking (give your single best guess as a short label, e.g. Hindi, Bhojpuri, Maithili, English).

Then produce one short response suitable for speaking aloud, in the SAME language/dialect the customer used, so the customer feels naturally understood.

Return exactly:

LANGUAGE_DETECTED: <your best guess>
REPLY: <one short sentence, in the same language as the customer>

Rules:
- The REPLY must be one sentence.
- Do not switch to English unless the customer spoke English.
- Do not explain your reasoning.
- Do not add anything before LANGUAGE_DETECTED or after REPLY."""

DEVANAGARI_RE = re.compile(r"[ऀ-ॿ]")
LATIN_RE = re.compile(r"[A-Za-z]")


def load_markers():
    if not MARKERS_PATH.exists():
        return {}
    data = json.loads(MARKERS_PATH.read_text())
    return data.get("markers", {})


def sample_dialect_inputs(dialect, n):
    path = DATA_DIR / f"{dialect}.jsonl"
    rows = []
    with open(path) as f:
        for line in f:
            r = json.loads(line)
            if r.get("error") or not r.get("prisma_transcript"):
                continue
            if len(r["prisma_transcript"].strip()) < 5:
                continue
            rows.append(r["prisma_transcript"])
    random.seed(hash(dialect) % (2**31))
    return random.sample(rows, min(n, len(rows)))


def call_evon(transcript, client):
    content = TASK_TEMPLATE.format(transcript=transcript)
    start = time.time()
    resp = client.post(EVON_URL, json={"model": EVON_MODEL, "messages": [{"role": "user", "content": content}]})
    latency = time.time() - start
    resp.raise_for_status()
    data = resp.json()
    raw = data["choices"][0]["message"]["content"]

    detected, reply = None, None
    if "LANGUAGE_DETECTED:" in raw:
        after = raw.split("LANGUAGE_DETECTED:", 1)[1]
        detected = after.split("\n")[0].strip()
        if "REPLY:" in after:
            detected = after.split("REPLY:")[0].strip()
    if "REPLY:" in raw:
        reply = raw.split("REPLY:", 1)[1].strip().split("\n")[0].strip()

    return {"raw": raw, "detected": detected, "reply": reply, "latency_sec": round(latency, 2)}


def classify_script(text):
    if not text:
        return "empty"
    has_dev = bool(DEVANAGARI_RE.search(text))
    has_lat = bool(LATIN_RE.search(text))
    if has_dev and not has_lat:
        return "devanagari"
    if has_lat and not has_dev:
        return "latin"
    if has_dev and has_lat:
        return "mixed"
    return "other"


def check_marker_presence(reply, dialect, markers_by_dialect):
    if not reply or dialect not in markers_by_dialect:
        return None
    dialect_markers = markers_by_dialect[dialect]
    found = [m for m in dialect_markers if m in reply]
    return found


def main():
    markers_by_dialect = load_markers()
    client = httpx.Client(timeout=httpx.Timeout(600, connect=10), follow_redirects=True)

    # Incremental checkpointing: append each result to JSONL as it completes,
    # so a kill/timeout mid-run doesn't lose everything (prior run lost 90+
    # completed calls because results were only written at the very end).
    jsonl_path = OUT_PATH.with_suffix(".jsonl")
    already_done = set()
    if jsonl_path.exists():
        with open(jsonl_path) as f:
            for line in f:
                try:
                    rec = json.loads(line)
                    already_done.add((rec["ground_truth"], rec["input_transcript"]))
                except Exception:
                    pass
        print(f"Resuming: {len(already_done)} already done")

    def run_one(ground_truth, transcript, out_fh, dialect_for_markers=None):
        if (ground_truth, transcript) in already_done:
            return
        r = call_evon(transcript, client)
        script = classify_script(r["reply"])
        markers_found = check_marker_presence(r["reply"], dialect_for_markers, markers_by_dialect) if dialect_for_markers else None
        record = {
            "ground_truth": ground_truth,
            "input_transcript": transcript,
            "detected": r["detected"],
            "reply": r["reply"],
            "reply_script": script,
            "dialect_markers_in_reply": markers_found,
            "latency_sec": r["latency_sec"],
            "raw": r["raw"],
        }
        out_fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        out_fh.flush()
        print(f"  in: {transcript[:40]!r}  detected={r['detected']!r}  reply={r['reply']!r}")

    with open(jsonl_path, "a") as out_fh:
        for dialect in DIALECTS:
            samples = sample_dialect_inputs(dialect, SAMPLES_PER_DIALECT)
            print(f"=== {dialect}: {len(samples)} samples ===")
            for transcript in samples:
                run_one(dialect, transcript, out_fh, dialect_for_markers=dialect)

        for label, controls in [("Hindi", HINDI_CONTROLS), ("English", ENGLISH_CONTROLS)]:
            print(f"=== {label} control ===")
            for transcript in controls:
                run_one(label, transcript, out_fh)

    # consolidate into the final JSON array
    results = []
    with open(jsonl_path) as f:
        for line in f:
            results.append(json.loads(line))
    with open(OUT_PATH, "w") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\nSaved {len(results)} results to {OUT_PATH}")


if __name__ == "__main__":
    main()
