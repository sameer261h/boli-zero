"""Pull a few Bhojpuri audio samples from the Vaani dataset for testing."""

import modal

app = modal.App("vaani-sample-fetch")

image = modal.Image.debian_slim(python_version="3.11").pip_install(
    "huggingface_hub", "pandas", "pyarrow"
)

volume = modal.Volume.from_name("vaani-samples", create_if_missing=True)
OUT_DIR = "/samples"


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("custom-secret")],
    volumes={OUT_DIR: volume},
    timeout=20 * 60,
)
def fetch_samples(n: int = 5):
    import os

    import pandas as pd
    from huggingface_hub import hf_hub_download

    path = hf_hub_download(
        repo_id="ARTPARK-IISc/Vaani",
        repo_type="dataset",
        filename="audio/Bhojpuri/train-00000-of-00143.parquet",
        token=os.environ["HF_TOKEN"],
    )

    df = pd.read_parquet(path)
    print("Columns:", list(df.columns))
    print("Row count in shard:", len(df))

    saved = []
    for i in range(min(n, len(df))):
        row = df.iloc[i]
        audio_bytes = row["audio"]["bytes"] if isinstance(row["audio"], dict) else row["audio"]
        out_path = f"{OUT_DIR}/sample_{i}.wav"
        with open(out_path, "wb") as f:
            f.write(audio_bytes)
        meta = {c: row[c] for c in df.columns if c != "audio"}
        saved.append({"file": out_path, "meta": meta})

    volume.commit()
    for s in saved:
        print(s)
    return saved
