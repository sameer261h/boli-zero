"""One-off: test Timbre TTS with a short text to confirm length was the issue."""

import modal

app = modal.App("timbre-length-test")
image = modal.Image.debian_slim(python_version="3.11").pip_install("requests")


@app.function(image=image, secrets=[modal.Secret.from_name("gnani-api-key")], timeout=60)
def test_short():
    import os

    import requests

    text = (
        "Based on the description, the function is most likely a Christmas "
        "celebration. The white and red outfit, the significant number of "
        "girl children, a few boys, and the setting in a nari seva sadan "
        "align with common NGO-style Christmas events."
    )
    resp = requests.post(
        "https://api.vachana.ai/api/v1/tts/inference",
        headers={"X-API-Key-ID": os.environ["GNANI_API_KEY"], "Content-Type": "application/json"},
        json={
            "text": text,
            "model": "timbre-v2.5",
            "voice": "Nalini",
            "language": "auto",
            "audio_config": {
                "encoding": "linear_pcm",
                "container": "wav",
                "num_channels": 1,
                "sample_rate": 48000,
                "sample_width": 2,
            },
        },
        timeout=60,
    )
    print("status:", resp.status_code)
    print("bytes:", len(resp.content))
    if not resp.ok:
        print("error body:", resp.text)
    return resp.status_code
