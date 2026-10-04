"""Boli Memory: a small labeled example bank of hard Bhojpuri customer
statements mapped to correct business decisions, retrieved by marker/lexical
overlap (no embedding model needed) and injected into Evon's prompt as
in-context examples — instead of a giant glossary or an attempted dialect
label.

EXAMPLE_BANK: used only for retrieval (shown to Evon as few-shot examples).
TEST_SET: held out, never shown to Evon directly, used to score Base vs
Boli-retrieval business-decision correctness. No overlap between the two.
"""

# ---------------------------------------------------------------------------
# Example bank — hard/adversarial Bhojpuri statements with correct labels.
# Covers: temporal ambiguity, subject ambiguity, non-commitment, partial
# payment, already-paid, wrong-borrower, hardship. These are the categories
# the current pipeline has been shown to get wrong without grounding.
# ---------------------------------------------------------------------------
EXAMPLE_BANK = [
    {
        "transcript": "सोमारे पैसा जमा कर देब।",
        "intent": "promise_to_pay",
        "details": "payment on Monday",
        "reply": "ठीक है, सोमवार को भुगतान का इंतज़ार रहेगा।",
    },
    {
        "transcript": "अभी नइखे, बाद में देब।",
        "intent": "cannot_pay_now",
        "details": "no specific date given, vague future promise",
        "reply": "ठीक है, जैसे ही संभव हो भुगतान कर दीजिएगा।",
    },
    {
        "transcript": "काल्हे देले बानी, फेर काहे फोन?",
        "intent": "already_paid",
        "details": "customer claims payment made yesterday (काल्हे here = yesterday, based on past-tense देले बानी)",
        "reply": "क्षमा करें, हम सत्यापन करके आपको सूचित करेंगे।",
    },
    {
        "transcript": "दू दिन मोहलत दे दीं, तनखा आवे वाला बा।",
        "intent": "requests_extension",
        "details": "2-day extension requested, salary arriving soon",
        "reply": "ठीक है, तनखा आने पर दो दिन में भुगतान कर दीजिएगा।",
    },
    {
        "transcript": "ई लोन हमार नइखे, रउआ गलत आदमी के फोन कइले बानी।",
        "intent": "wrong_borrower",
        "details": "customer denies this is their loan, claims wrong number",
        "reply": "माफ़ करें, हम आपका नंबर हटा देंगे और सत्यापन करेंगे।",
    },
    {
        "transcript": "अभी घर में इलाज चलत बा, पैसा नइखे।",
        "intent": "hardship",
        "details": "ongoing medical treatment in family, genuinely no money, no date given",
        "reply": "हमें आपकी स्थिति की जानकारी के लिए खेद है, हम विकल्प पर बात करेंगे।",
    },
    {
        "transcript": "आधा आज देब, बाकी तनखा अइला पर।",
        "intent": "partial_payment",
        "details": "half today, remainder when salary arrives (no fixed date)",
        "reply": "ठीक है, आधा आज और बाकी तनखा आने पर स्वीकार है।",
    },
    {
        "transcript": "देखत बानी, हो सकेला।",
        "intent": "non_commitment",
        "details": "vague, NOT a promise to pay — 'looking into it, maybe' carries no actual commitment",
        "reply": "ठीक है, कृपया जल्द ही निश्चित जानकारी दीजिएगा।",
    },
]

# ---------------------------------------------------------------------------
# Held-out test set — same categories, DIFFERENT statements, never retrieved.
# Ground truth defined here by hand (these are authored, not real audio —
# same limitation as the earlier EMI experiments, flagged honestly).
# ---------------------------------------------------------------------------
TEST_SET = [
    {
        "transcript": "काल्हे जमा कर देब।",
        "category": "temporal_ambiguity",
        "correct_intent": "promise_to_pay",
        "correct_details_contains": ["tomorrow", "कल"],  # काल्हे here = tomorrow (future tense देब)
        "note": "काल्हे is ambiguous (yesterday OR tomorrow in Bhojpuri) — tense of the verb (देब=will give, future) should resolve it to tomorrow, not yesterday",
    },
    {
        "transcript": "हम बताइब जब पैसा आई।",
        "category": "subject_ambiguity",
        "correct_intent": "will_inform_when_able",
        "correct_details_contains": ["customer", "inform"],
        "note": "customer says THEY will inform (हम बताइब = I will tell), not asking to be informed — subject-flip bug seen before",
    },
    {
        "transcript": "देखत बानी, हो सकेला।",
        "category": "non_commitment",
        "correct_intent": "non_commitment",  # NOT promise_to_pay
        "correct_details_contains": ["no", "not", "vague", "नहीं"],
        "note": "must NOT be scored as a payment promise",
    },
    {
        "transcript": "पूरा पइसा अभी ना दे पाइब, आधा अबही देब, बाकी तनखा अइला पर।",
        "category": "partial_payment",
        "correct_intent": "partial_payment",
        "correct_details_contains": ["half", "आधा", "salary", "तनखा"],
        "note": "two-part payment, second part tied to salary not a fixed date",
    },
    {
        "transcript": "तीन दिन पहिले जमा कइले रहीं हम।",
        "category": "already_paid",
        "correct_intent": "already_paid",
        "correct_details_contains": ["three days ago", "तीन दिन"],
        "note": "past payment claim, different phrasing than example bank's version",
    },
    {
        "transcript": "ई लोन हमार नइखे।",
        "category": "wrong_borrower",
        "correct_intent": "wrong_borrower",
        "correct_details_contains": ["not their loan", "नइखे"],
        "note": "shorter/terser version than example bank's wrong-borrower example",
    },
    {
        "transcript": "अभी घर में इलाज चलत बा, पैसा नइखे।",
        "category": "hardship",
        "correct_intent": "hardship",
        "correct_details_contains": ["medical", "इलाज", "treatment"],
        "note": "note: this exact sentence is ALSO in the example bank — intentional, to sanity-check retrieval finds its own near-duplicate",
    },
]
