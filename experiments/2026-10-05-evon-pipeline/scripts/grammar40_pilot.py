"""40-parameter grammar importance pilot on the frozen shared 999-clip manifest (prisma_transcript only)."""
import json, math, sys, warnings
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold
sys.path.insert(0, str(Path(__file__).parent))
import grammar40_lexicon as G
warnings.filterwarnings("ignore")

HERE = Path(__file__).resolve().parent.parent
MAN = HERE / "data" / "shared_1k_audio_manifest.jsonl"
OUTD = HERE / "data" / "grammar40_pilot"; OUTD.mkdir(exist_ok=True)
LANGS = ["Hindi", "Bhojpuri", "Maithili", "Chhattisgarhi", "Rajasthani", "Garhwali", "Khariboli", "Kumaoni"]
FAM = {"Hindi": "Western-Hindi", "Khariboli": "Western-Hindi", "Bhojpuri": "Bihari", "Maithili": "Bihari",
       "Chhattisgarhi": "Eastern-Hindi", "Rajasthani": "Rajasthani", "Garhwali": "Pahari", "Kumaoni": "Pahari"}
FAMS = sorted(set(FAM.values()))
REPS, W = 8, dict(abl=.40, dis=.25, pre=.15, cov=.10, sta=.10)
ABL_FULL_SCALE, H_FULL_SCALE, COV_FULL = 0.03, 0.6, 0.5

rows = [json.loads(l) for l in open(MAN)]
n = len(rows); lang = np.array([r["language"] for r in rows]); fam = np.array([FAM[l] for l in lang])
shard = np.array([r["shard"] for r in rows])
X = np.zeros((n, 40), int); hits = [defaultdict(Counter) for _ in range(n)]
for i, r in enumerate(rows):
    for c, lab in G.match(r["prisma_transcript"]):
        X[i, c - 1] = 1; hits[i][c][lab] += 1
fires_total = X.sum(0)

def h(p, q): return abs(2 * math.asin(math.sqrt(p)) - 2 * math.asin(math.sqrt(q)))
def status(s, cov):
    if s is None: return "zero"
    return "core" if s >= 80 else "strong" if s >= 60 else "supporting" if s >= 40 else "weak" if s >= 20 else "negligible" if s >= 1 else "zero"

# ---- ablation: leave-one-parameter-out, repeated stratified CV, per-class OvR AUC ----------------
def cv_auc(Xm, y, classes):
    out = np.zeros((REPS, len(classes)))
    for rep in range(REPS):
        P = np.zeros((len(y), len(classes)))
        for tr, te in StratifiedKFold(5, shuffle=True, random_state=rep).split(Xm, y):
            m = LogisticRegression(C=0.5, class_weight="balanced", max_iter=400).fit(Xm[tr], y[tr])
            P[te] = m.predict_proba(Xm[te])
        out[rep] = [roc_auc_score(y == c, P[:, k]) for k, c in enumerate(classes)]
    return out  # reps x classes
def ablate(labels, classes):
    y = np.array([classes.index(l) for l in labels]); full = cv_auc(X, y, list(range(len(classes))))
    drops = np.zeros((40, len(classes), REPS))
    for p in range(40):
        if fires_total[p] == 0: continue
        keep = [j for j in range(40) if j != p]
        drops[p] = (full - cv_auc(X[:, keep], y, list(range(len(classes))))).T
    return full, drops
fullL, dropL = ablate(list(lang), LANGS)
fullF, dropF = ablate(list(fam), FAMS)

# ---- per-parameter component metrics ------------------------------------------------------------
def folds_by_shard(idx, k=3):
    sizes = Counter(shard[idx]); bins = [[0, []] for _ in range(k)]
    for s, c in sorted(sizes.items(), key=lambda t: -t[1]):
        b = min(bins, key=lambda b: b[0]); b[0] += c; b[1].append(s)
    return [np.array([i for i in idx if shard[i] in set(b[1])]) for b in bins if b[1]]
def stability(cells, p):
    cells = [c for c in cells if len(c) >= 25]
    if len(cells) < 2: return None
    r = np.array([X[c, p].mean() for c in cells]); nn = np.array([len(c) for c in cells])
    if r.mean() == 0: return None
    var_excess = max(0, r.var(ddof=1) - np.mean(r * (1 - r) / nn))
    return 100 * (1 - min(1, math.sqrt(var_excess) / r.mean()))
def composite(comp):
    avail = {k: v for k, v in comp.items() if v is not None}
    s = sum(W[k] * avail[k] for k in avail) / sum(W[k] for k in avail)
    return s, (comp["abl"] is None)

def score_unit(members_mask_langs, others_langs, unit_idx, other_groups, drops_p, fires_u, p, cells):
    """members: list of language names forming the unit; computes metrics for parameter p."""
    pass

def eval_unit(unit_langs, unit_rows, other_langs_groups, drop_mean, drop_sd, p, cells_fn, nunits):
    rU = np.mean([X[lang == l, p].mean() for l in unit_langs])
    rO = [np.mean([X[lang == l, p].mean() for l in g]) for g in other_langs_groups]
    nU = len(unit_rows); firesU = int(X[unit_rows, p].sum())
    cov = rU
    cov_s = min(100, 100 * cov / COV_FULL)
    nO = n - nU
    se = math.sqrt(1 / nU + len(other_langs_groups) / nO)
    dis = h(rU, np.mean(rO)); dis_s = min(100, 100 * max(0, dis - se) / H_FULL_SCALE)
    tot = rU + sum(rO)
    pre_s = None
    if firesU >= 3 and tot > 0:
        pre_s = 100 * max(0, (rU / tot - 1 / nunits) / (1 - 1 / nunits))
    sta = stability(cells_fn(), p) if firesU >= 5 else None
    abl_s = None if fires_total[p] < 5 else 100 * min(1, max(0, drop_mean - drop_sd) / ABL_FULL_SCALE)
    return dict(cov=cov_s, dis=dis_s, pre=pre_s, sta=sta, abl=abl_s), dict(cov_raw=cov, dir=('present' if rU > np.mean(rO) else 'absent'), fires=firesU, h=dis, drop=drop_mean, drop_sd=drop_sd)

results = {}
for li, L in enumerate(LANGS):
    idx = np.where(lang == L)[0]; F = FAM[L]; fl = [l for l in LANGS if FAM[l] == F]; fidx = np.where(fam == F)[0]
    fi = FAMS.index(F); params = []
    for p in range(40):
        pid = p + 1
        if fires_total[p] == 0:
            params.append(dict(id=pid, name=G.NAMES[p], coverage=0.0, distinctiveness=None, precision=None, stability=None,
                               ablation_value=0.0, exact_language_score=0.0, family_score=0.0, rank=None, status="zero",
                               observed_markers=[], notes="No marker of this class occurs anywhere in the 999 Prisma transcripts (lexicon match = 0)."))
            continue
        # exact language
        comp, raw = eval_unit([L], idx, [[l] for l in LANGS if l != L], dropL[p, li].mean(), dropL[p, li].std(), p,
                              lambda: folds_by_shard(idx), len(LANGS))
        es, partial = composite(comp)
        if partial: es = min(es, 19.0)
        # family
        compF, rawF = eval_unit(fl, fidx, [[l for l in LANGS if FAM[l] == f] for f in FAMS if f != F], dropF[p, fi].mean(),
                                dropF[p, fi].std(), p,
                                (lambda: [np.where(lang == l)[0] for l in fl]) if len(fl) > 1 else (lambda: folds_by_shard(idx)), len(FAMS))
        fs, fpartial = composite(compF)
        if fpartial: fs = min(fs, 19.0)
        # markers
        cL, cO = Counter(), Counter()
        for i in range(n):
            for lab in hits[i][pid]:
                (cL if lang[i] == L else cO)[lab] += 1
        mk = sorted(cL, key=lambda m: (-(cL[m] / len(idx)) / ((cO[m] + .5) / (n - len(idx))), -cL[m]))
        mk = [f"{m} [{cL[m]} in {L} / {cO[m]} elsewhere]" for m in sorted(cL, key=lambda m: -cL[m]) if cL[m] >= 2][:8] if False else \
             [f"{m} [{cL[m]} in {L} / {cO[m]} elsewhere]" for m in mk if cL[m] >= 2][:8]
        note = f"fires in {raw['fires']}/{len(idx)} {L} rows, {int(fires_total[p])}/999 overall; ablation AUC drop {raw['drop']:+.4f}±{raw['drop_sd']:.4f} (lang), {rawF['drop']:+.4f}±{rawF['drop_sd']:.4f} (family)."
        note = f"signal={raw['dir']}-driven (language rate {'above' if raw['dir']=='present' else 'below'} other languages). " + note
        if partial: note += " Ablation not estimable (<5 firing rows overall): score capped at 19."
        if comp["pre"] is None: note += " precision=null (<3 firing rows in language)."
        if comp["sta"] is None: note += " stability=null (<5 firing rows or <2 usable cells)."
        params.append(dict(id=pid, name=G.NAMES[p], coverage=round(raw["cov_raw"] * 100, 1), distinctiveness=round(comp["dis"], 1),
                           precision=None if comp["pre"] is None else round(comp["pre"], 1),
                           stability=None if comp["sta"] is None else round(comp["sta"], 1),
                           ablation_value=None if comp["abl"] is None else round(comp["abl"], 1),
                           exact_language_score=round(es, 1), family_score=round(fs, 1), rank=None,
                           status=status(es, raw["cov_raw"]) if raw["fires"] else ("zero" if es < 1 else status(es, 0)),
                           observed_markers=mk, notes=note))
    order = sorted(params, key=lambda q: (-q["exact_language_score"], -(q["coverage"] or 0), q["id"]))
    prev, rk = None, 0
    for pos, q in enumerate(order, 1):
        if q["exact_language_score"] != prev: rk = pos; prev = q["exact_language_score"]
        q["rank"] = rk
    results[L] = dict(language=L, family=FAM[L], n_clips=int(len(idx)), parameters=sorted(params, key=lambda q: q["id"]))
    assert len(params) == 40

json.dump(dict(manifest=str(MAN.name), n_rows=n, method=dict(weights=W, reps=REPS, scales=dict(ablation_auc=ABL_FULL_SCALE, h=H_FULL_SCALE, coverage=COV_FULL),
          full_model_auc={L: round(float(fullL[:, i].mean()), 3) for i, L in enumerate(LANGS)}, family_auc={f: round(float(fullF[:, i].mean()), 3) for i, f in enumerate(FAMS)}),
          languages=results), open(OUTD / "results.json", "w"), ensure_ascii=False, indent=1)

# ---- report -------------------------------------------------------------------------------------
md = ["# 40-parameter grammar pilot (999-clip shared manifest, prisma_transcript)\n"]
cross = defaultdict(lambda: ([], []))
f = lambda v: "null" if v is None else f"{v:g}"
for L in LANGS:
    ps = sorted(results[L]["parameters"], key=lambda q: (q["rank"], q["id"]))
    useful = [q for q in ps if q["exact_language_score"] >= 40]; some = [q for q in ps if q["exact_language_score"] >= 20]
    zero = [q for q in ps if q["exact_language_score"] < 1]
    md += [f"\n## {L} (family: {FAM[L]}; n={results[L]['n_clips']}; full-model OvR AUC={fullL[:, LANGS.index(L)].mean():.3f})",
           f"- materially useful (score>=40): **{len(useful)}**; weak-or-better (>=20): {len(some)}; effectively zero (<1): {len(zero)}",
           "- top 5: " + "; ".join(f"{q['name']} ({q['exact_language_score']})" for q in ps[:5]),
           "- of the useful ones, absence-driven: " + (", ".join(q["name"] for q in useful if "signal=absent" in q["notes"]) or "none"),
           "- zero: " + (", ".join(q["name"] for q in zero) or "none"),
           "- exact vs family: " + "; ".join(f"{q['name']} exact {q['exact_language_score']} / family {q['family_score']}" for q in ps[:5]),
           "\n| rank | parameter | coverage% | distinct | precision | stability | ablation | exact | family | status | observed markers |", "|--|--|--|--|--|--|--|--|--|--|--|"]
    for q in ps:
        md.append(f"| {q['rank']} | {q['id']}. {q['name']} | {f(q['coverage'])} | {f(q['distinctiveness'])} | {f(q['precision'])} | {f(q['stability'])} | {f(q['ablation_value'])} | {q['exact_language_score']} | {q['family_score']} | {q['status']} | {q['notes'].split('-driven')[0].replace('signal=','') if 'signal=' in q['notes'] else '-'} | {'; '.join(q['observed_markers'][:4])} |")
    for q in ps:
        (cross[q["id"]][0] if q["exact_language_score"] >= 40 else cross[q["id"]][1] if q["exact_language_score"] < 20 else []).append(L) if True else None
md += ["\n## Cross-language summary (important = exact score >=40; weak/zero = <20)\n", "| parameter | languages where important | languages where weak/zero |", "|--|--|--|"]
for pid in range(1, 41):
    a, b = cross[pid]; md.append(f"| {pid}. {G.NAMES[pid-1]} | {', '.join(a) or '-'} | {', '.join(b) or '-'} |")
(OUTD / "report.md").write_text("\n".join(md))
print("\n".join(md[:1]), {L: round(float(fullL[:, i].mean()), 3) for i, L in enumerate(LANGS)}, {f: round(float(fullF[:, i].mean()), 3) for i, f in enumerate(FAMS)})
print("fires per class:", dict(enumerate(fires_total.tolist(), 1)))
