"""Allosaurus phonotactic language-ID feasibility test on the frozen shared
1k manifest (data/shared_1k_audio_manifest.jsonl).

  audio -> Allosaurus (frozen, universal IPA inventory) -> phone sequence
        -> phone uni/bi/trigram TF-IDF -> logistic regression

Inputs to the classifier are ONLY phone n-grams from audio. No transcripts
(human or Prisma), no metadata. Metadata is used only to build the split.

Stages:
  phones   -- run Allosaurus on every manifest clip, cache to
              data/allosaurus_lid/phones.jsonl (resumable). Audio is fetched
              from the gated Vaani shard named in the manifest and only held
              in a scratch temp file.
  analyze  -- grouped CV classifiers, ablations, shuffled-label control,
              marker tables -> data/allosaurus_lid/results.json

Split: 5-fold StratifiedGroupKFold, group = state|district (a whole district,
both genders, never appears in train and test of the same fold), so speaker,
district and district-level recording-session identity cannot leak. Every
clip gets exactly one out-of-fold prediction.
"""

import io
import json
import sys
import tempfile
import wave
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

DATA = Path(__file__).resolve().parent.parent / "data"
MANIFEST = DATA / "shared_1k_audio_manifest.jsonl"
OUT_DIR = DATA / "allosaurus_lid"
PHONES = OUT_DIR / "phones.jsonl"
RESULTS = OUT_DIR / "results.json"
LANGS = ["Hindi", "Bhojpuri", "Maithili", "Chhattisgarhi", "Rajasthani", "Garhwali", "Khariboli", "Kumaoni"]
SEED = 0


def load_manifest():
    return [json.loads(l) for l in open(MANIFEST)]


# ---------------------------------------------------------------- phones

def to_16k_mono_wav(b):
    from scipy.signal import resample_poly
    with wave.open(io.BytesIO(b), "rb") as w:
        sr, ch, sw = w.getframerate(), w.getnchannels(), w.getsampwidth()
        raw = w.readframes(w.getnframes())
    assert sw == 2, f"unexpected sample width {sw}"
    x = np.frombuffer(raw, dtype=np.int16).astype(np.float32)
    if ch > 1:
        x = x.reshape(-1, ch).mean(1)
    if sr != 16000:
        from math import gcd
        g = gcd(sr, 16000)
        x = resample_poly(x, 16000 // g, sr // g)
    x = np.clip(x, -32768, 32767).astype(np.int16)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000)
        w.writeframes(x.tobytes())
    return buf.getvalue(), sr


def run_phones():
    import pandas as pd
    from allosaurus.app import read_recognizer
    from huggingface_hub import hf_hub_download

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    done = set()
    if PHONES.exists():
        done = {json.loads(l)["sample_id"] for l in open(PHONES)}
    rows = [r for r in load_manifest() if r["sample_id"] not in done]
    print(f"{len(done)} cached, {len(rows)} to run")
    model = read_recognizer()  # default = latest universal model (uni2005)
    by_shard = defaultdict(list)
    for r in rows:
        by_shard[(r["dataset"], r["shard"])].append(r)
    with open(PHONES, "a") as out, tempfile.TemporaryDirectory() as td:
        for (ds, shard), rs in by_shard.items():
            df = pd.read_parquet(hf_hub_download(ds, shard, repo_type="dataset"), columns=["audio"])
            for r in rs:
                rec = {"sample_id": r["sample_id"], "language": r["language"]}
                try:
                    a = df.iloc[r["row_idx"]]["audio"]
                    b = a["bytes"] if isinstance(a, dict) else a
                    wav, sr = to_16k_mono_wav(b)
                    p = Path(td) / "x.wav"
                    p.write_bytes(wav)
                    rec["phones"] = model.recognize(str(p)).split()
                    rec["orig_sr"] = sr
                except Exception as e:  # unusable audio row -- recorded, not dropped silently
                    rec["error"] = repr(e)
                out.write(json.dumps(rec, ensure_ascii=False) + "\n")
                out.flush()
            print(f"  {shard}: {len(rs)} done")


# ---------------------------------------------------------------- analysis

def ngrams(ph, n):
    return ["-".join(ph[i:i + n]) for i in range(len(ph) - n + 1)]


def featurize(ph, ns):
    toks = []
    for n in ns:
        toks += ngrams(ph, n)
    return toks


ABLATIONS = {"uni": (1,), "bi": (2,), "tri": (3,), "uni+bi": (1, 2), "uni+bi+tri": (1, 2, 3)}


def make_vec(ns):
    from sklearn.feature_extraction.text import TfidfVectorizer
    return TfidfVectorizer(analyzer=lambda ph: featurize(ph, ns), min_df=3, sublinear_tf=True)


def make_clf():
    from sklearn.linear_model import LogisticRegression
    return LogisticRegression(C=1.0, max_iter=5000, class_weight="balanced")


def cv_predict(X_phones, y, groups, ns, shuffle=False):
    from sklearn.model_selection import StratifiedGroupKFold
    rng = np.random.RandomState(SEED)
    pred = np.empty(len(y), dtype=object)
    skf = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=SEED)
    for tr, te in skf.split(np.zeros(len(y)), y, groups):
        ytr = y[tr].copy()
        if shuffle:
            ytr = rng.permutation(ytr)
        vec = make_vec(ns)
        Xtr = vec.fit_transform([X_phones[i] for i in tr])
        clf = make_clf().fit(Xtr, ytr)
        pred[te] = clf.predict(vec.transform([X_phones[i] for i in te]))
    return pred


def metrics(y, p, labels):
    from sklearn.metrics import balanced_accuracy_score, confusion_matrix, f1_score, precision_recall_fscore_support
    pr, rc, f1, sup = precision_recall_fscore_support(y, p, labels=labels, zero_division=0)
    return {
        "balanced_accuracy": round(balanced_accuracy_score(y, p), 4),
        "macro_f1": round(f1_score(y, p, labels=labels, average="macro", zero_division=0), 4),
        "per_class": {l: {"precision": round(pr[i], 3), "recall": round(rc[i], 3), "f1": round(f1[i], 3), "n": int(sup[i])}
                      for i, l in enumerate(labels)},
        "labels": labels,
        "confusion": confusion_matrix(y, p, labels=labels).tolist(),
    }


def marker_table(X_phones, y, langs, clf, vec, top=10, min_cov=0.05):
    """For each language: top positive-weight n-grams with coverage/enrichment."""
    vocab = vec.get_feature_names_out()
    sets = [set(featurize(ph, (1, 2, 3))) for ph in X_phones]
    idx = {l: np.where(y == l)[0] for l in langs}

    def cov(f, l):
        return float(np.mean([f in sets[i] for i in idx[l]]))

    def cov_not(f, l):
        ii = np.where(y != l)[0]
        return float(np.mean([f in sets[i] for i in ii]))

    out = {}
    classes = list(clf.classes_)
    W = clf.coef_
    for l in langs:
        if W.shape[0] == 1:  # binary: row is weight toward classes_[1]
            w = W[0] if classes[1] == l else -W[0]
        else:
            w = W[classes.index(l)]
        rows = []
        for j in np.argsort(-w):
            f = vocab[j]
            c = cov(f, l)
            if c < min_cov:
                continue
            co = cov_not(f, l)
            ch = cov(f, "Hindi") if l != "Hindi" and "Hindi" in idx else None
            rows.append({
                "pattern": f, "n": f.count("-") + 1, "coverage": round(c, 3),
                "coverage_others": round(co, 3),
                "enrichment_vs_others": round((c + 0.01) / (co + 0.01), 2),
                "enrichment_vs_hindi": round((c + 0.01) / (ch + 0.01), 2) if ch is not None else None,
                "weight": round(float(w[j]), 3),
            })
            if len(rows) >= top:
                break
        out[l] = rows
    return out


def analyze():
    from sklearn.metrics import confusion_matrix

    man = {r["sample_id"]: r for r in load_manifest()}
    recs = [json.loads(l) for l in open(PHONES)]
    errors = [r for r in recs if "error" in r]
    recs = [r for r in recs if "error" not in r and r["phones"]]
    X = [r["phones"] for r in recs]
    meta = [man[r["sample_id"]] for r in recs]
    y8 = np.array([m["language"] for m in meta])
    yA = np.where(y8 == "Hindi", "Hindi", "Regional")
    groups = np.array([f"{m['state']}|{m['district']}" for m in meta])
    dur = np.array([m["duration_sec"] for m in meta])
    nph = np.array([len(p) for p in X])

    res = {"n_clips": len(recs), "unusable": [{"sample_id": e["sample_id"], "error": e["error"]} for e in errors]}
    res["clips_per_language"] = dict(Counter(y8))
    res["duration"] = {"mean": round(float(dur.mean()), 2), "median": round(float(np.median(dur)), 2),
                       "per_language_mean": {l: round(float(dur[y8 == l].mean()), 2) for l in LANGS}}
    res["phones_per_sec"] = {l: round(float((nph / dur)[y8 == l].mean()), 2) for l in LANGS}
    res["phones_per_clip_mean"] = round(float(nph.mean()), 1)

    # leakage audit: districts shared across languages (cannot split those apart by group)
    dl = defaultdict(set)
    for g, l in zip(groups, y8):
        dl[g].add(l)
    res["n_district_groups"] = len(dl)
    res["districts_with_multiple_languages"] = {g: sorted(v) for g, v in dl.items() if len(v) > 1}

    res["examples"] = [{"sample_id": recs[i]["sample_id"], "language": y8[i], "duration_sec": dur[i],
                        "phones": " ".join(X[i])} for i in [0, len(recs) // 2, len(recs) - 1]]

    # --- tasks + ablation
    res["taskA"], res["taskB"] = {}, {}
    for name, ns in ABLATIONS.items():
        pA = cv_predict(X, yA, groups, ns)
        pB = cv_predict(X, y8, groups, ns)
        res["taskA"][name] = metrics(yA, pA, ["Hindi", "Regional"])
        res["taskB"][name] = metrics(y8, pB, LANGS)
        print(f"{name:12} A bal_acc={res['taskA'][name]['balanced_accuracy']}  B bal_acc={res['taskB'][name]['balanced_accuracy']} macroF1={res['taskB'][name]['macro_f1']}")

    # --- Hindi-vs-regional with Hindi-recall per regional language (best config)
    full = (1, 2, 3)
    pA = cv_predict(X, yA, groups, full)
    res["taskA_regional_called_hindi_rate"] = {l: round(float(np.mean(pA[y8 == l] == "Hindi")), 3) for l in LANGS}

    # --- confusion pairs (8-way full)
    cm = np.array(res["taskB"]["uni+bi+tri"]["confusion"])
    pairs = [(LANGS[i], LANGS[j], int(cm[i, j])) for i in range(8) for j in range(8) if i != j]
    res["top_confusion_pairs"] = sorted(pairs, key=lambda t: -t[2])[:8]

    # --- shuffled-label control
    res["shuffled"] = {
        "taskA": metrics(yA, cv_predict(X, yA, groups, full, shuffle=True), ["Hindi", "Regional"])["balanced_accuracy"],
        "taskB": metrics(y8, cv_predict(X, y8, groups, full, shuffle=True), LANGS)["balanced_accuracy"],
    }
    print("shuffled", res["shuffled"])

    # --- markers: models fit on ALL data (descriptive, not evaluation)
    vec = make_vec(full)
    Xall = vec.fit_transform(X)
    clfB = make_clf().fit(Xall, y8)
    res["markers_8way"] = marker_table(X, y8, LANGS, clfB, vec)
    clfA = make_clf().fit(Xall, yA)
    res["markers_hindi_vs_regional"] = marker_table(X, yA, ["Hindi", "Regional"], clfA, vec, top=15)

    # family-shared: enriched vs Hindi (>=1.5x, cov>=5%) in >=5 of 7 regional
    sets = [set(featurize(ph, full)) for ph in X]
    feats = vec.get_feature_names_out()
    covs = {}
    for l in LANGS:
        ii = np.where(y8 == l)[0]
        cnt = Counter()
        for i in ii:
            cnt.update(sets[i] & set(feats))
        covs[l] = {f: cnt[f] / len(ii) for f in feats}
    fam = []
    for f in feats:
        h = covs["Hindi"][f]
        enr = [l for l in LANGS[1:] if covs[l][f] >= 0.05 and (covs[l][f] + 0.01) / (h + 0.01) >= 1.5]
        if len(enr) >= 5:
            fam.append({"pattern": f, "enriched_in": enr, "hindi_cov": round(h, 3),
                        "mean_regional_cov": round(float(np.mean([covs[l][f] for l in LANGS[1:]])), 3)})
    res["family_shared_vs_hindi"] = sorted(fam, key=lambda d: -(d["mean_regional_cov"] + 0.01) / (d["hindi_cov"] + 0.01))[:15]

    # close-relative pairs: grouped-CV pair accuracy + top distinguishing patterns
    res["close_pairs"] = {}
    for a, b in [("Bhojpuri", "Maithili"), ("Garhwali", "Kumaoni"), ("Hindi", "Khariboli"), ("Rajasthani", "Khariboli")]:
        m = np.isin(y8, [a, b])
        Xp = [X[i] for i in np.where(m)[0]]
        pp = cv_predict(Xp, y8[m], groups[m], full)
        v = make_vec(full); Xm = v.fit_transform(Xp)
        c = make_clf().fit(Xm, y8[m])
        res["close_pairs"][f"{a}_vs_{b}"] = {
            "balanced_accuracy": metrics(y8[m], pp, [a, b])["balanced_accuracy"],
            "markers": marker_table(Xp, y8[m], [a, b], c, v, top=5),
        }

    RESULTS.write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str))
    print(f"-> {RESULTS}")


if __name__ == "__main__":
    {"phones": run_phones, "analyze": analyze}[sys.argv[1]]()
