"""Derive corpus-based markers for every available Hindi-family dialect in
Vaani-transcription-part, vs a shared Hindi reference corpus. Same method as
the Bhojpuri derivation, generalized across dialects.
"""

import modal

app = modal.App("derive-markers-multi")
image = modal.Image.debian_slim(python_version="3.11").pip_install(
    "huggingface_hub", "pandas", "pyarrow"
)

# Hindi-family / Hindi-adjacent dialects relevant to the "Prisma transcribes
# via hi-IN" use case. Excludes unrelated languages (Tamil, Bengali, etc.)
# that already have their own supported Prisma/Timbre language codes.
CANDIDATE_DIALECTS = [
    "Bhojpuri", "Awadhi", "Maithili", "Magahi", "Angika", "Bajjika",
    "Chhattisgarhi", "Bundeli", "Haryanvi", "Garhwali", "Khortha",
    "Marwari", "Mewari", "Malvi", "Nimadi", "Rajasthani", "Sadri",
    "Surjapuri", "Kumaoni", "Harauti", "Jaipuri", "Wagdi", "Mewati",
    "Khariboli", "Powari", "Surgujia", "Pahadi", "Shekhawati",
]


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("custom-secret")],
    timeout=30 * 60,
    memory=16384,
)
def derive_all():
    import os
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

    def load_transcripts(file_list, max_files=2):
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

    # Load Hindi reference once, reused for every dialect comparison.
    hindi_files = sorted([f for f in files if "/Hindi/" in f and f.endswith(".parquet")])
    print(f"Loading Hindi reference from {len(hindi_files)} available files (using 4)...")
    hindi_texts = load_transcripts(hindi_files, max_files=4)
    hin_words = tokenize(hindi_texts)
    hin_counts = Counter(hin_words)
    hin_total = sum(hin_counts.values())
    print(f"Hindi reference: {len(hindi_texts)} transcripts, {hin_total} words\n")

    # Which candidate dialects actually have files available?
    available = {}
    for dialect in CANDIDATE_DIALECTS:
        matches = sorted([f for f in files if f"/{dialect}/" in f and f.endswith(".parquet")])
        if matches:
            available[dialect] = matches
    print(f"Dialects with transcript files available: {list(available.keys())}\n")

    all_results = {}
    for dialect, dfiles in available.items():
        print(f"=== {dialect} ({len(dfiles)} files available) ===")
        texts = load_transcripts(dfiles, max_files=3)
        if len(texts) < 50:
            print(f"  skipping — only {len(texts)} transcripts, too few\n")
            continue
        words = tokenize(texts)
        counts = Counter(words)
        total = sum(counts.values())

        scored = []
        for word, freq in counts.items():
            if freq < 3 or len(word) < 2:
                continue
            hin_freq = hin_counts.get(word, 0)
            rate = freq / total
            hin_rate = hin_freq / hin_total if hin_total else 0
            ratio = rate / (hin_rate + 1e-7)
            if hin_freq == 0 or ratio > 20:  # meaningfully distinctive
                scored.append((word, freq, hin_freq, round(ratio, 1)))
        scored.sort(key=lambda x: (-x[3], -x[1]))

        top = scored[:40]
        print(f"  {len(texts)} transcripts, {total} words, {len(top)} distinctive markers found")
        for word, bf, hf, ratio in top[:10]:
            print(f"    {word}  (freq={bf}, hindi_freq={hf})")
        print()
        all_results[dialect] = {
            "transcript_count": len(texts),
            "word_count": total,
            "markers": top,
        }

    return all_results


@app.local_entrypoint()
def main():
    import json

    result = derive_all.remote()
    with open("multi_dialect_markers.json", "w") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print("\nSaved to multi_dialect_markers.json")
    print("\nSummary:")
    for dialect, data in result.items():
        print(f"  {dialect}: {len(data['markers'])} markers from {data['transcript_count']} transcripts")
