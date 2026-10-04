"""Derive Bhojpuri dialect markers from real corpus frequency, not hand-picking.

Pull Bhojpuri and Hindi transcripts from Vaani-transcription-part, compare word
frequencies, and surface words that are statistically over-represented in
Bhojpuri relative to Hindi — real evidence-based markers.
"""

import modal

app = modal.App("derive-markers-from-corpus")
image = modal.Image.debian_slim(python_version="3.11").pip_install(
    "huggingface_hub", "pandas", "pyarrow"
)


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("custom-secret")],
    timeout=15 * 60,
    memory=16384,
)
def derive_markers():
    import os
    import re
    from collections import Counter

    import pandas as pd
    from huggingface_hub import HfApi, hf_hub_download

    token = os.environ["HF_TOKEN"]
    api = HfApi(token=token)

    # Find what files exist for Bhojpuri and Hindi in the transcription dataset
    files = api.list_repo_files("ARTPARK-IISc/Vaani-transcription-part", repo_type="dataset")
    bhojpuri_files = [f for f in files if "Bhojpuri" in f and f.endswith(".parquet")]
    hindi_files = [f for f in files if f.startswith("audio/Hindi/") and f.endswith(".parquet")] or [
        f for f in files if "/Hindi/" in f and f.endswith(".parquet")
    ]

    print(f"Bhojpuri parquet files found: {len(bhojpuri_files)}")
    print(bhojpuri_files[:5])
    print(f"Hindi parquet files found: {len(hindi_files)}")
    print(hindi_files[:5])

    def load_transcripts(file_list, max_files=3):
        texts = []
        for f in file_list[:max_files]:
            path = hf_hub_download(
                "ARTPARK-IISc/Vaani-transcription-part", f, repo_type="dataset", token=token
            )
            df = pd.read_parquet(path, columns=None)
            text_col = None
            for c in df.columns:
                if "transcript" in c.lower() or "text" in c.lower():
                    text_col = c
                    break
            if text_col:
                texts.extend(df[text_col].dropna().astype(str).tolist())
            print(f"  loaded {f}: {len(df)} rows, text_col={text_col}")
        return texts

    bhojpuri_texts = load_transcripts(bhojpuri_files)
    hindi_texts = load_transcripts(hindi_files)

    print(f"\nTotal Bhojpuri transcripts: {len(bhojpuri_texts)}")
    print(f"Total Hindi transcripts: {len(hindi_texts)}")

    def tokenize(texts):
        words = []
        for t in texts:
            words.extend(re.findall(r"[ऀ-ॿ]+", t))
        return words

    bho_words = tokenize(bhojpuri_texts)
    hin_words = tokenize(hindi_texts)

    bho_counts = Counter(bho_words)
    hin_counts = Counter(hin_words)
    hin_total = sum(hin_counts.values())
    bho_total = sum(bho_counts.values())

    # Score: words frequent in Bhojpuri but rare/absent in Hindi (relative rate)
    scored = []
    for word, bho_freq in bho_counts.items():
        if bho_freq < 3 or len(word) < 2:
            continue
        hin_freq = hin_counts.get(word, 0)
        bho_rate = bho_freq / bho_total
        hin_rate = hin_freq / hin_total if hin_total else 0
        ratio = bho_rate / (hin_rate + 1e-7)
        scored.append((word, bho_freq, hin_freq, round(ratio, 1)))

    scored.sort(key=lambda x: (-x[3], -x[1]))

    print("\n=== Top 50 Bhojpuri-distinctive words (freq in Bhojpuri / freq in Hindi / ratio) ===")
    for word, bf, hf, ratio in scored[:50]:
        print(f"{word}\t bho={bf}\t hin={hf}\t ratio={ratio}")

    return scored[:100]


@app.local_entrypoint()
def main():
    result = derive_markers.remote()
    import json

    with open("corpus_derived_markers.json", "w") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print("\nSaved to corpus_derived_markers.json")
