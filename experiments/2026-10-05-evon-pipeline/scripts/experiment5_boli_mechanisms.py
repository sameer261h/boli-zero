"""3 ambiguous telecom-support statements (Bhojpuri-spoken, Hindi-written) x
3 mechanisms for making Evon's reply sound Bhojpuri while staying in Devanagari
(never naming "Bhojpuri" as a language target to the model, which earlier
caused script corruption). 9 responses total.
"""

import json
import re

import requests

EVON_URL = "https://sameer261h--evon-v3-3-serve-serve.modal.run/v1/chat/completions"
EVON_MODEL = "/weights/gnani/gnani-evon-v3.3-30B-A3B"

# Ambiguous, reasoning-requiring customer statements — telecom support, written
# in Devanagari with real Bhojpuri grammar/vocabulary.
PHRASES = {
    "P1_mixed_complaint": (
        "रउआ लोग के नेटवर्क एकदम बेकार बा, पइसा त हर महीना कटते रहेला, ई त ठीक नइखे।"
    ),  # ambiguous: network complaint or billing complaint, or both — which to address first?
    "P2_churn_threat": (
        "अब आर कुछ ना कहब, बस कनेक्शन कटवा के दोसरा कंपनी में चल जाइब।"
    ),  # no explicit request — implied churn risk, agent must infer retention need
    "P3_vague_intermittent": (
        "कल रात से फोन में कुछ अइसन होता बा, कभी चले ला कभी ना चले ला, रिचार्ज कइले बानी फेरो।"
    ),  # vague symptom + mentions re-recharging — network issue or billing/balance confusion?
}

BASE_TASK = """You are a customer support agent for a telecom company.

The customer said:

{transcript}

Understand what the customer means and respond helpfully in one short spoken sentence.

Return exactly:

REPLY: <one short Hindi sentence>

Rules:
- One sentence, short enough to say on a phone call.
- Do not explain your reasoning.
- Do not add analysis before or after the required format."""

# Mechanism B: lexicon card given, "Bhojpuri" never named.
LEXICON_CARD = """Some regional speech forms you may find natural to use in your reply:

- है -> बा
- देंगे -> देब
- नहीं है -> नइखे
- आप -> रउआ
- कर दिया -> कइले बानी
- चला जाऊंगा -> चल जाइब
- कटवा दूंगा -> कटवा देब

Feel free to use these forms naturally where they fit, without changing the meaning.

"""

# Mechanism C: few-shot style pairs, no language named.
FEWSHOT_CARD = """Here are two examples of the speaking style to use in your reply:

Example 1:
Standard: "ठीक है, मैं कल आपकी समस्या ठीक कर दूंगा।"
Styled:   "ठीक बा, हम काल्हे रउआ के समस्या ठीक कर देब।"

Example 2:
Standard: "क्षमा करें, यह नहीं हो सकता है।"
Styled:   "माफ करीं, ई नइखे हो सकत।"

Write your REPLY in this same speaking style.

"""

# Mechanism A dictionary — deterministic post-substitution on a plain Hindi reply.
SUBSTITUTIONS = [
    (r"\bहै\b", "बा"),
    (r"\bहूं\b", "बानी"),
    (r"\bदूंगा\b", "देब"),
    (r"\bदेंगे\b", "देब"),
    (r"\bनहीं है\b", "नइखे"),
    (r"\bआप\b", "रउआ"),
    (r"\bकर दिया\b", "कइले बानी"),
    (r"\bकल\b", "काल्हे"),
    (r"\bक्षमा करें\b", "माफ करीं"),
]


def call_evon(content):
    resp = requests.post(
        EVON_URL,
        json={"model": EVON_MODEL, "messages": [{"role": "user", "content": content}]},
        timeout=600,
    )
    resp.raise_for_status()
    raw = resp.json()["choices"][0]["message"]["content"]
    final = raw.rsplit("</think>", 1)[-1].strip()
    reply = None
    if "REPLY:" in final:
        reply = final.split("REPLY:", 1)[1].strip().split("\n")[0].strip()
    return raw, final, reply


def apply_substitution(text):
    out = text
    for pattern, replacement in SUBSTITUTIONS:
        out = re.sub(pattern, replacement, out)
    return out


def main():
    results = {}
    for key, transcript in PHRASES.items():
        print(f"=== {key} ===")
        base_content = BASE_TASK.format(transcript=transcript)

        # Step 2: baseline Evon reply (plain Hindi, no dialect instruction)
        raw_base, final_base, reply_base = call_evon(base_content)
        print("  baseline reply:", reply_base)

        # Mechanism A: deterministic substitution on the baseline reply
        reply_a = apply_substitution(reply_base) if reply_base else None
        print("  mech A (substitution):", reply_a)

        # Mechanism B: lexicon card + base task, same call structure
        content_b = LEXICON_CARD + base_content
        raw_b, final_b, reply_b = call_evon(content_b)
        print("  mech B (lexicon card):", reply_b)

        # Mechanism C: few-shot style card + base task
        content_c = FEWSHOT_CARD + base_content
        raw_c, final_c, reply_c = call_evon(content_c)
        print("  mech C (few-shot style):", reply_c)

        results[key] = {
            "transcript": transcript,
            "baseline_reply": reply_base,
            "baseline_raw": raw_base,
            "mechanism_A_substitution": reply_a,
            "mechanism_B_lexicon_card": {"reply": reply_b, "raw": raw_b},
            "mechanism_C_fewshot_style": {"reply": reply_c, "raw": raw_c},
        }

    with open("experiment5_results.json", "w") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("\nSaved to experiment5_results.json")


if __name__ == "__main__":
    main()
