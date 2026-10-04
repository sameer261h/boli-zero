"""Test Timbre with a medium-length (1135 char) reply to find the real limit."""

import json

import modal

app = modal.App("timbre-length-test-2")
image = modal.Image.debian_slim(python_version="3.11").pip_install("requests")


@app.function(image=image, secrets=[modal.Secret.from_name("gnani-api-key")], timeout=60)
def test_medium(payload: dict):
    import os

    import requests

    resp = requests.post(
        "https://api.vachana.ai/api/v1/tts/inference",
        headers={"X-API-Key-ID": os.environ["GNANI_API_KEY"], "Content-Type": "application/json"},
        json=payload,
        timeout=60,
    )
    print("status:", resp.status_code)
    print("bytes:", len(resp.content))
    if not resp.ok:
        print("error body:", resp.text)
    return resp.status_code


@app.local_entrypoint()
def main():
    with open("tts_test_medium.json") as f:
        payload = json.load(f)
    test_medium.remote(payload)
