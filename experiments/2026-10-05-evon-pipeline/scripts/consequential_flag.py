import sys
sys.path.insert(0, "scripts")
from phonetic_filter_classification import classify_pair
from analyze_prisma_fingerprint import clean, tokenize, load_dialect, align, DIALECTS
from collections import Counter

global_pair_counts = Counter()
for dialect in DIALECTS:
    rows = load_dialect(dialect)
    for r in rows:
        h_tokens = tokenize(r["human_transcript"]); p_tokens = tokenize(r["prisma_transcript"])
        if not h_tokens or h_tokens == p_tokens: continue
        for tag, h_span, p_span in align(h_tokens, p_tokens):
            if tag == "replace" and len(h_span)==1 and len(p_span)==1:
                x,y = h_span[0], p_span[0]
                if x!=y: global_pair_counts[(x,y)] += 1

# groups now include the dialectal SOURCE forms that produce each standard target,
# not just the standard forms themselves (the bug in the first pass)
GROUPS = [
    {"है","हैं","हे","हेय","हई","छे","छीये","बा","बाटे","हल","हो","व","वा","च","छिये","ए"},  # copula "is/are/am"
    {"ये","यह","इ","ई","एहा"},  # near-demonstrative "this"
    {"वह","वो"},  # far-demonstrative "that" (kept separate from "here/there" adverbs)
    {"यहाँ","यहां","इहा"},  # "here"
    {"वहाँ","वहां"},  # "there"
    {"रही","रहे","रहा","रहीं","रो","रहियो","रेहो","रियो","रिया","रा"},  # progressive marker, dialectal verb endings included
    {"और","अउ","अऊ","अ"},  # "and"
    {"नहीं","नई","नी","ने"},  # negation "no/not"
    {"का","की","के"},  # possessive, gender/number only
    {"हाँ","हां","ह"},  # "yes"
    {"में","म","मा"},  # "in/at" -- dialectal shortened forms
    {"भी","बि"},  # "also"
    {"एक","एगो","एको"},  # "one/a" -- Bhojpuri numeral classifier normalized, meaning-preserving
    {"गई","गयी"}, {"हुआ","हुवा"}, {"सीसा","शीशा"}, {"बहार","बाहर"},
    {"आवो","आओ"}, {"बोडो","बड़ा"}, {"हवय","हवे","हावय"}, {"भौत","भोत","बोहोत","बहुत"},
]
AMBIGUOUS_SOURCE_WORDS = {"ओ", "एगो"}  # split between meaning-preserving and meaning-changing targets

def group_of(w):
    for i,g in enumerate(GROUPS):
        if w in g: return i
    return None

wrong_pairs = [((x,y),c) for (x,y),c in global_pair_counts.items() if classify_pair(x,y)[0]=="WRONG"]
total_wrong = sum(c for _,c in wrong_pairs)
can_live, needs_fixing, ambiguous_source = 0, 0, 0
needs_fixing_examples = []
for (x,y),c in wrong_pairs:
    if x in AMBIGUOUS_SOURCE_WORDS:
        ambiguous_source += c
        continue
    gx, gy = group_of(x), group_of(y)
    if gx is not None and gx == gy:
        can_live += c
    else:
        needs_fixing += c
        needs_fixing_examples.append(((x,y),c))

needs_fixing_examples.sort(key=lambda kv: -kv[1])
print(f"Total WRONG: {total_wrong}")
print(f"  Can live with (same functional group): {can_live} ({can_live/total_wrong:.1%})")
print(f"  Needs fixing (different meaning/category): {needs_fixing} ({needs_fixing/total_wrong:.1%})")
print(f"  Ambiguous source word (ओ/एगो -- splits between both, context-dependent): {ambiguous_source} ({ambiguous_source/total_wrong:.1%})")
print(f"\nAs % of ALL 38,705 differences:")
print(f"  Can live with: {can_live/38705:.1%}")
print(f"  Needs fixing: {needs_fixing/38705:.1%}")
print(f"  Ambiguous source: {ambiguous_source/38705:.1%}")
print(f"\nTop 25 'needs fixing' examples (real finding, not group-bug):")
for (x,y),c in needs_fixing_examples[:25]:
    print(f"  {x!r} -> {y!r}  x{c}")
