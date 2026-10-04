"""Boli experiment 2: business instructions alone vs business + dialect grounding.
5 customer statements x 2 conditions = 10 Evon calls. Prisma is NOT evaluated here
per instructions — these 5 transcripts are given as already-final Prisma output.
"""

import json
import time

import requests

EVON_URL = "https://sameer261h--evon-v3-3-serve-serve.modal.run/v1/chat/completions"
EVON_MODEL = "/weights/gnani/gnani-evon-v3.3-30B-A3B"

STATEMENTS = {
    "1_tomorrow": "अभी पइसा नइखे, काल्हे जमा कर देब।",
    "2_monday": "आज पइसा ना बा, सोमारे दे देब।",
    "3_two_days": "दू दिन अउरी मोहलत दे दीं, तनखा आवे वाला बा।",
    "4_already_paid": "हम त काल्हे पइसा जमा कर देले बानी, फेर काहे फोन आ रहल बा?",
    "5_half_now": "पूरा पइसा अभी ना दे पाइब, आधा आज देब बाकी अगिला हफ्ता।",
}

TASK_TEMPLATE = """You are the reasoning engine for an EMI collections voice agent.

The customer's EMI is currently due.

The customer said:

{transcript}

Understand what the customer means.

Identify:

- the customer's intent
- any payment date or duration
- any important payment detail

Then produce one short response suitable for speaking aloud to the customer.

Return exactly:

INTENT: <short intent>
DETAILS: <important details>
REPLY: <one short Hindi sentence>

Rules:

- The REPLY must be one sentence.
- Keep it short enough for a phone conversation.
- Do not explain your reasoning.
- Do not provide multiple possible interpretations.
- Do not write an essay.
- Do not add analysis before or after the required format."""

BOLI_CARD = """The customer may use regional Bhojpuri speech.

Useful regional forms:

- पइसा = पैसा
- नइखे = नहीं है
- ना बा = नहीं है
- काल्हे = कल
- सोमारे = सोमवार को
- देब = दूंगा / देंगे
- दू = दो
- अउरी = और
- दीं = दीजिए
- आवे वाला बा = आने वाला है
- देले बानी = दे चुका / भुगतान कर चुका
- काहे = क्यों
- अगिला = अगला
- ना दे पाइब = नहीं दे पाऊंगा

Use this only to understand the customer's meaning.

"""


def call_evon(content):
    start = time.time()
    resp = requests.post(
        EVON_URL,
        json={"model": EVON_MODEL, "messages": [{"role": "user", "content": content}]},
        timeout=600,
    )
    latency = time.time() - start
    resp.raise_for_status()
    data = resp.json()
    choice = data["choices"][0]
    raw = choice["message"]["content"]

    # Extract REPLY: line
    reply = None
    if "REPLY:" in raw:
        reply = raw.split("REPLY:", 1)[1].strip()
        # take first line only, in case of trailing junk
        reply = reply.split("\n")[0].strip()

    return {
        "request_content": content,
        "raw_output": raw,
        "reply_extracted": reply,
        "char_count": len(raw),
        "completion_tokens": data.get("usage", {}).get("completion_tokens"),
        "latency_sec": round(latency, 2),
    }


def main():
    results = {}
    for key, transcript in STATEMENTS.items():
        print(f"=== {key} ===")

        print("  Condition A (business only)...")
        content_a = TASK_TEMPLATE.format(transcript=transcript)
        results[f"{key}_A"] = call_evon(content_a)
        results[f"{key}_A"]["condition"] = "A_business"
        results[f"{key}_A"]["transcript"] = transcript
        print(f"    reply: {results[f'{key}_A']['reply_extracted']}")

        print("  Condition B (business + Boli card)...")
        content_b = BOLI_CARD + TASK_TEMPLATE.format(transcript=transcript)
        results[f"{key}_B"] = call_evon(content_b)
        results[f"{key}_B"]["condition"] = "B_boli"
        results[f"{key}_B"]["transcript"] = transcript
        print(f"    reply: {results[f'{key}_B']['reply_extracted']}")

    with open("experiment2_evon_results.json", "w") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("\nSaved to experiment2_evon_results.json")


if __name__ == "__main__":
    main()
