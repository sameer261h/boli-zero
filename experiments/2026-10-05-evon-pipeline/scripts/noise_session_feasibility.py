"""Feasibility check: does background-noise/acoustic-environment clustering
reveal real sub-structure within one of our existing district+gender groups?

Hypothesis: a single state|district|gender "group" (our current speaker-proxy)
likely merges MULTIPLE real recording sessions/speakers under one label. If
clips from the same actual session share a consistent background-noise /
room-acoustic signature (room tone, hum, reverb character) even though
speech content differs, clustering on that signature could reveal how many
real sessions are hiding inside one group -- a cheap, audio-only proxy that
doesn't require full speaker-embedding ML.

Bounded test: pull ~120 clips from ONE large, suspicious group (Khortha's
Jamtara-Male, 542 rows, a WEAK-severity dialect where one group dominates),
extract a per-clip "noise floor" spectral fingerprint (MFCCs computed only
on the quietest frames of each clip, under the assumption those frames are
background noise, not speech), cluster, and check: does k>1 clearly beat
k=1 (one real cluster, i.e. consistent environment) by silhouette score?

If yes: worth scaling up. If no (or ambiguous): the signal isn't there,
don't invest further without saying so.
"""

import sys
from pathlib import Path

import numpy as np
import librosa
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prisma_fingerprint_pull import REPO, list_dialect_files, find_text_col, find_audio_col, iter_rows
from huggingface_hub import HfApi, hf_hub_download
import pandas as pd
import io

TARGET_DIALECT = "Khortha"
TARGET_DISTRICT = "Jamtara"
TARGET_GENDER = "Male"
N_SAMPLE = 120

api = HfApi()


def noise_floor_mfcc(audio_bytes, sr_target=16000, n_mfcc=13, noise_percentile=20):
    y, sr = librosa.load(io.BytesIO(audio_bytes), sr=sr_target, mono=True)
    if len(y) < sr * 0.3:  # too short to be useful
        return None
    frame_length = int(0.025 * sr)
    hop_length = int(0.010 * sr)
    rms = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]
    if len(rms) < 5:
        return None
    thresh = np.percentile(rms, noise_percentile)
    noise_frame_idx = np.where(rms <= thresh)[0]
    if len(noise_frame_idx) < 3:
        return None
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=n_mfcc, hop_length=hop_length)
    # guard against frame-count mismatch between rms and mfcc hop alignment
    valid_idx = noise_frame_idx[noise_frame_idx < mfcc.shape[1]]
    if len(valid_idx) < 3:
        return None
    noise_mfcc = mfcc[:, valid_idx].mean(axis=1)
    return noise_mfcc


def main():
    print(f"Fetching rows for {TARGET_DIALECT} / {TARGET_DISTRICT} / {TARGET_GENDER}...")
    files = list_dialect_files(api, TARGET_DIALECT)
    collected = []
    for f in files:
        path = hf_hub_download(REPO, f, repo_type="dataset")
        df = pd.read_parquet(path)
        text_col = find_text_col(df)
        audio_col = find_audio_col(df)
        if not text_col or not audio_col:
            continue
        for row_idx, text, audio_bytes, meta in iter_rows(df, text_col, audio_col):
            if meta.get("district") != TARGET_DISTRICT or meta.get("gender") != TARGET_GENDER:
                continue
            collected.append((f, row_idx, audio_bytes))
            if len(collected) >= N_SAMPLE:
                break
        if len(collected) >= N_SAMPLE:
            break
    print(f"Collected {len(collected)} clips. Extracting noise-floor MFCC features...")

    feats, kept = [], []
    for i, (shard, row_idx, audio_bytes) in enumerate(collected):
        try:
            f = noise_floor_mfcc(audio_bytes)
        except Exception as e:
            f = None
        if f is not None:
            feats.append(f)
            kept.append((shard, row_idx))
        if (i + 1) % 20 == 0:
            print(f"  {i+1}/{len(collected)} processed, {len(feats)} usable so far")

    X = np.array(feats)
    print(f"\nUsable feature vectors: {X.shape}")
    if X.shape[0] < 10:
        print("Too few usable clips to test clustering. Stopping.")
        return

    # standardize
    X = (X - X.mean(axis=0)) / (X.std(axis=0) + 1e-8)

    print("\n=== Silhouette score by k (k=1 baseline has no silhouette; compare k=2..8) ===")
    best_k, best_s = None, -2
    for k in range(2, min(9, X.shape[0] // 3)):
        km = KMeans(n_clusters=k, n_init=10, random_state=42)
        labels = km.fit_predict(X)
        s = silhouette_score(X, labels)
        sizes = np.bincount(labels)
        print(f"  k={k}: silhouette={s:.4f}  cluster_sizes={sorted(sizes, reverse=True)}")
        if s > best_s:
            best_s, best_k = s, k

    print(f"\nBest k: {best_k} (silhouette={best_s:.4f})")
    print("Rule of thumb: silhouette > 0.5 = strong real clusters (multiple sessions likely hiding in this group).")
    print("0.25-0.5 = some structure, worth a closer look. <0.25 = no clear sub-structure (looks like one consistent environment).")


if __name__ == "__main__":
    main()
