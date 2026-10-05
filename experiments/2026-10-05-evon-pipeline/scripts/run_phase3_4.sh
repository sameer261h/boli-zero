#!/usr/bin/env bash
# Runs unattended once the Hindi pull parts finish: retry errors, merge, Phase 2 report, Phase 3, Phase 4a/4b.
# Usage: nohup bash run_phase3_4.sh > ../data/markers/run_phase3_4.log 2>&1 &
set -u
cd "$(dirname "$0")"
D=../data
M=$D/markers
wait_pull() { while pgrep -f "^python3 hindi_pull.py" > /dev/null; do sleep 20; done; }

echo "[$(date +%T)] waiting for pull parts"; wait_pull
echo "[$(date +%T)] retry pass for errored clips"
for k in 0 1 2; do python3 hindi_pull.py --nparts 3 --part $k --concurrency 3 > $D/prisma_fingerprint/hindi/pull_retry$k.log 2>&1 & done
wait
python3 hindi_merge.py

echo "[$(date +%T)] phase 2 report"
python3 phase2_report.py > $M/phase2_report.txt 2>&1

echo "[$(date +%T)] phase 3: 20-class marker runs"
for k in "" "--strict"; do
  for s in 0 1 2 3 4; do python3 phase1_markers.py --hindi $k --seed $s > /dev/null 2>&1 || echo "FAIL phase3 $k $s"; done
done
python3 phase1_report.py --hindi > $M/phase3_report_stdout.txt 2>&1
echo "[$(date +%T)] phase 3 done"

echo "[$(date +%T)] phase 4a: picture-topic check"
python3 phase4_topic.py > $M/phase4_topic_stdout.txt 2>&1

echo "[$(date +%T)] phase 4b: leave-one-variety-out (6 configs, 3 at a time)"
for s in 0 1 2; do python3 phase4_lovo.py --seed $s > $M/phase4_lovo_primary_s$s.log 2>&1 & done
wait
for s in 0 1 2; do python3 phase4_lovo.py --seed $s --strict > $M/phase4_lovo_strict_s$s.log 2>&1 & done
wait
python3 phase4_lovo.py --aggregate > $M/phase4_lovo_stdout.txt 2>&1
python3 phase4_report.py > $M/phase4_report_stdout.txt 2>&1
echo "[$(date +%T)] ALL DONE"
