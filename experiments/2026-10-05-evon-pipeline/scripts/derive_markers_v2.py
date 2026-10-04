"""Corpus-derived dialect markers, v2:
1. Cross-dialect discrimination — a marker shared across multiple dialects
   (e.g. Bhojpuri+Magahi+Bajjika all use it) gets downweighted, not just
   checked against Hindi.
2. Held-out evaluation — markers derived from 80% of each dialect's
   transcripts, accuracy measured on the untouched 20%, so we don't
   overestimate by validating on the same data that built the markers.
"""

import modal

app = modal.App("derive-markers-v2")
image = modal.Image.debian_slim(python_version="3.11").pip_install(
    "huggingface_hub", "pandas", "pyarrow"
)

STRONG_DIALECTS = [
    "Bhojpuri", "Maithili", "Magahi", "Bajjika", "Angika",
    "Chhattisgarhi", "Garhwali", "Marwari", "Rajasthani", "Kumaoni", "Khortha",
]
EXPERIMENTAL_DIALECTS = ["Sadri", "Surgujia", "Bundeli"]
ALL_DIALECTS = STRONG_DIALECTS + EXPERIMENTAL_DIALECTS


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("custom-secret")],
    timeout=40 * 60,
    memory=16384,
)
def derive_v2():
    import os
    import random
    import re
    from collections import Counter

    import pandas as pd
    from huggingface_hub import HfApi, hf_hub_download

    token = os.environ["HF_TOKEN"]
    api = HfApi(token=token)
    files = api.list_repo_files("ARTPARK-IISc/Vaani-transcription-part", repo_type="dataset")

    def tokenize(texts):
        words = []
        for t in texts:
            words.extend(re.findall(r"[ऀ-ॿ]+", t))
        return words

    def load_transcripts(file_list, max_files=4):
        texts = []
        for f in file_list[:max_files]:
            try:
                path = hf_hub_download(
                    "ARTPARK-IISc/Vaani-transcription-part", f, repo_type="dataset", token=token
                )
                df = pd.read_parquet(path)
                text_col = next((c for c in df.columns if "transcript" in c.lower()), None)
                if text_col:
                    texts.extend(df[text_col].dropna().astype(str).tolist())
            except Exception as e:
                print(f"    skip {f}: {e}")
        return texts

    random.seed(42)

    # --- Load everything, split 80/20 per dialect, build train-split word counts ---
    print("Loading Hindi reference...")
    hindi_files = sorted([f for f in files if "/Hindi/" in f and f.endswith(".parquet")])
    hindi_texts = load_transcripts(hindi_files, max_files=4)
    hin_counts = Counter(tokenize(hindi_texts))
    hin_total = sum(hin_counts.values())
    print(f"  Hindi: {len(hindi_texts)} transcripts, {hin_total} words\n")

    dialect_data = {}  # dialect -> {"train_counts", "train_total", "eval_texts"}
    for dialect in ALL_DIALECTS:
        dfiles = sorted([f for f in files if f"/{dialect}/" in f and f.endswith(".parquet")])
        if not dfiles:
            print(f"{dialect}: no files, skipping")
            continue
        texts = load_transcripts(dfiles, max_files=4)
        if len(texts) < 50:
            print(f"{dialect}: only {len(texts)} transcripts, skipping")
            continue
        random.shuffle(texts)
        split = int(len(texts) * 0.8)
        train_texts, eval_texts = texts[:split], texts[split:]
        train_counts = Counter(tokenize(train_texts))
        dialect_data[dialect] = {
            "train_counts": train_counts,
            "train_total": sum(train_counts.values()),
            "eval_texts": eval_texts,
        }
        print(f"{dialect}: {len(texts)} transcripts ({len(train_texts)} train / {len(eval_texts)} eval)")

    print()

    # --- Step 1: candidate markers per dialect, distinctive vs Hindi (train split only) ---
    candidates = {}  # dialect -> set of candidate marker words
    for dialect, data in dialect_data.items():
        cands = set()
        for word, freq in data["train_counts"].items():
            if freq < 3 or len(word) < 2:
                continue
            hin_freq = hin_counts.get(word, 0)
            rate = freq / data["train_total"]
            hin_rate = hin_freq / hin_total if hin_total else 0
            ratio = rate / (hin_rate + 1e-7)
            if hin_freq == 0 or ratio > 20:
                cands.add(word)
        candidates[dialect] = cands
        print(f"{dialect}: {len(cands)} candidate markers (distinctive vs Hindi)")

    print()

    # --- Step 2: cross-dialect discrimination weighting ---
    # For each candidate marker in dialect X, count how many OTHER dialects
    # also use it with meaningful frequency (>=3 occurrences in their train set).
    final_markers = {}  # dialect -> {marker: weight}
    for dialect, cands in candidates.items():
        weighted = {}
        for word in cands:
            dialects_using_it = 1  # itself
            for other, other_data in dialect_data.items():
                if other == dialect:
                    continue
                if other_data["train_counts"].get(word, 0) >= 3:
                    dialects_using_it += 1
            weight = 1.0 / dialects_using_it
            weighted[word] = weight
        # Keep only markers with weight >= 0.5 (appears substantially in at most 1 other dialect)
        pure = {w: wt for w, wt in weighted.items() if wt >= 0.5}
        final_markers[dialect] = pure
        shared_dropped = len(weighted) - len(pure)
        print(f"{dialect}: {len(pure)} markers after cross-dialect weighting ({shared_dropped} dropped as shared)")

    print()

    # --- Step 3: held-out evaluation ---
    # For each dialect's eval transcripts, score against every dialect's final
    # marker set, see if the correct dialect wins (or falls to hindi/unknown).
    def score_transcript(text, marker_sets, saturation, threshold, margin):
        scores = {}
        for d, markers in marker_sets.items():
            matched_weight = sum(wt for w, wt in markers.items() if w in text)
            scores[d] = min(1.0, matched_weight / saturation)
        ranked = sorted(scores.items(), key=lambda x: -x[1])
        top_d, top_score = ranked[0]
        second_score = ranked[1][1] if len(ranked) > 1 else 0.0
        if top_score < threshold or (top_score - second_score) < margin:
            return "hindi_unknown", scores
        return top_d, scores

    # Cache raw eval texts for reuse across threshold sweeps (avoid re-downloading)
    eval_texts_by_dialect = {d: data["eval_texts"] for d, data in dialect_data.items()}

    def run_eval(saturation, threshold, margin, label):
        print(f"\n=== Held-out evaluation: {label} (saturation={saturation}, threshold={threshold}, margin={margin}) ===")
        confusion = {d: Counter() for d in final_markers}
        for true_dialect, texts in eval_texts_by_dialect.items():
            if true_dialect not in final_markers:
                continue
            for text in texts:
                predicted, _ = score_transcript(text, final_markers, saturation, threshold, margin)
                confusion[true_dialect][predicted] += 1
        overall_correct, overall_total = 0, 0
        summary = {}
        for true_dialect, preds in confusion.items():
            total = sum(preds.values())
            correct = preds.get(true_dialect, 0)
            overall_correct += correct
            overall_total += total
            acc = correct / total if total else 0
            print(f"  {true_dialect}: {correct}/{total} ({acc:.0%}) — {dict(preds.most_common(3))}")
            summary[true_dialect] = {"accuracy": round(acc, 3), "confusion": dict(preds)}
        overall_acc = overall_correct / overall_total if overall_total else 0
        print(f"  OVERALL: {overall_correct}/{overall_total} ({overall_acc:.0%})")
        return summary, overall_acc

    # Sweep: original strict settings, then progressively looser
    sweep_configs = [
        (3, 0.67, 0.15, "original (strict)"),
        (2, 0.5, 0.15, "looser saturation=2, threshold=0.5"),
        (1, 0.34, 0.1, "loosest saturation=1 (any single marker), threshold=0.34"),
        (1, 0.34, 0.0, "loosest + no margin requirement"),
    ]
    sweep_results = {}
    for saturation, threshold, margin, label in sweep_configs:
        summary, overall_acc = run_eval(saturation, threshold, margin, label)
        sweep_results[label] = {"overall_accuracy": round(overall_acc, 3), "per_dialect": summary}

    return {
        "markers": {d: m for d, m in final_markers.items()},
        "threshold_sweep": sweep_results,
    }


@app.local_entrypoint()
def main():
    import json

    result = derive_v2.remote()
    with open("markers_v2.json", "w") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print("\nSaved to markers_v2.json")
