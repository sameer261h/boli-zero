"""Evon v3.3 BF16 served via vLLM's OpenAI-compatible server, on Modal.

No system prompt, no language instruction, no post-processing — raw model
in, raw model out. Model weights cached in a Modal Volume so repeat runs
don't re-download 60GB+ every time.
"""

import modal

MODEL_NAME = "gnani/gnani-evon-v3.3-30B-A3B"

app = modal.App("evon-v3-3-serve")

volume = modal.Volume.from_name("evon-weights", create_if_missing=True)
MODEL_DIR = "/weights"

image = (
    modal.Image.from_registry("nvidia/cuda:12.8.0-devel-ubuntu22.04", add_python="3.11")
    .apt_install("git")
    .pip_install(
        "vllm>=0.6.0",
        "huggingface_hub[hf_transfer]",
        "transformers>=4.44.0",
    )
    .env({"HF_HUB_ENABLE_HF_TRANSFER": "1"})
)


@app.function(
    image=image,
    volumes={MODEL_DIR: volume},
    timeout=60 * 60,
)
def download_model():
    from huggingface_hub import snapshot_download

    snapshot_download(
        MODEL_NAME,
        local_dir=f"{MODEL_DIR}/{MODEL_NAME}",
        local_dir_use_symlinks=False,
    )
    volume.commit()
    print("Download complete.")


@app.function(
    image=image,
    gpu="A100-80GB",
    volumes={MODEL_DIR: volume},
    timeout=60 * 60 * 2,
    min_containers=0,
    max_containers=1,
    # 5 minutes, not 60: an idle A100 bills the whole window after the last request.
    scaledown_window=5 * 60,
    memory=131072,
)
# Without this Modal sends the container one request at a time, so vLLM never batches and concurrent callers queue.
@modal.concurrent(max_inputs=32)
@modal.web_server(port=8000, startup_timeout=60 * 10)
def serve():
    import subprocess

    subprocess.Popen(
        [
            "vllm",
            "serve",
            f"{MODEL_DIR}/{MODEL_NAME}",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--dtype", "bfloat16",
        ]
    )
