import csv
import sys
sys.path.insert(0, "scripts")
from phonetic_filter_classification import classify_pair
from analyze_prisma_fingerprint import clean, tokenize, load_dialect, align, DIALECTS
from collections import Counter
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate

GROUPS = [
    {"है","हैं","हे","हेय","हई","छे","छीये","बा","बाटे","हल","हो","व","वा","च","छिये","ए"},
    {"ये","यह","इ","ई","एहा"}, {"वह","वो"}, {"यहाँ","यहां","इहा"}, {"वहाँ","वहां"},
    {"रही","रहे","रहा","रहीं","रो","रहियो","रेहो","रियो","रिया","रा"},
    {"और","अउ","अऊ","अ"}, {"नहीं","नई","नी","ने"}, {"का","की","के"}, {"हाँ","हां","ह"},
    {"में","म","मा"}, {"भी","बि"}, {"एक","एगो","एको"},
    {"गई","गयी"}, {"हुआ","हुवा"}, {"सीसा","शीशा"}, {"बहार","बाहर"},
    {"आवो","आओ"}, {"बोडो","बड़ा"}, {"हवय","हवे","हावय"}, {"भौत","भोत","बोहोत","बहुत"},
]
AMBIGUOUS_SOURCE_WORDS = {"ओ", "एगो"}
def group_of(w):
    for i,g in enumerate(GROUPS):
        if w in g: return i
    return None

def roman(w):
    try:
        return transliterate(w, sanscript.DEVANAGARI, sanscript.ITRANS)
    except Exception:
        return ""

pair_dialect_counts = Counter()  # (dialect, x, y) -> count
for dialect in DIALECTS:
    rows = load_dialect(dialect)
    for r in rows:
        h_tokens = tokenize(r["human_transcript"]); p_tokens = tokenize(r["prisma_transcript"])
        if not h_tokens or h_tokens == p_tokens: continue
        for tag, h_span, p_span in align(h_tokens, p_tokens):
            if tag == "replace" and len(h_span)==1 and len(p_span)==1:
                x,y = h_span[0], p_span[0]
                if x!=y: pair_dialect_counts[(dialect,x,y)] += 1

rows_out = []
total_check = 0
for (dialect,x,y), c in pair_dialect_counts.items():
    label, _ = classify_pair(x,y)
    if label != "WRONG": continue
    if x in AMBIGUOUS_SOURCE_WORDS: continue
    gx, gy = group_of(x), group_of(y)
    if gx is not None and gx == gy: continue  # can-live-with, skip
    rows_out.append({
        "dialect": dialect,
        "human_word": x, "human_word_roman": roman(x),
        "prisma_word": y, "prisma_word_roman": roman(y),
        "count": c,
    })
    total_check += c

rows_out.sort(key=lambda r: -r["count"])
print(f"Total rows (unique dialect,human,prisma triples): {len(rows_out)}")
print(f"Total instance count (should be 7327): {total_check}")

out_path = "/home/user/boli-zero/experiments/2026-10-05-evon-pipeline/data/prisma_fingerprint/regional_fingerprint_audit/needs_fixing_wrong_substitutions.csv"
with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=["dialect","human_word","human_word_roman","prisma_word","prisma_word_roman","count"])
    writer.writeheader()
    writer.writerows(rows_out)
print(f"Saved to {out_path}")
