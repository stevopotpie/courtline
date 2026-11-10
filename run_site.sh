#!/usr/bin/env bash
# Rebuild Courtline: fetch the hoopR NBA data, run the model, build the site into docs/.
# Usage: bash run_site.sh REPO_DIR   (hoopR data is cached in REPO_DIR/hoopr, which git ignores)
set -euo pipefail
W="${1:-$(pwd)}"
H="$W/hoopr"
if [ -d "$H/.git" ]; then
  git -C "$H" pull -q --depth 1 origin HEAD || echo "hoopr: pull failed, using the copy on disk"
else
  git clone -q --depth 1 --filter=blob:none --no-checkout https://github.com/sportsdataverse/hoopR-nba-data "$H"
  git -C "$H" sparse-checkout set --no-cone 'nba/team_box/parquet/team_box_20*.parquet' 'nba/schedules/parquet/nba_schedule_20*.parquet' 'nba/betting_lines/*'
  git -C "$H" checkout -q
fi
echo "hoopr data: $(git -C "$H" log -1 --format='%ci %s')"
python3 -I -W ignore "$W/model.py" "$H" "$W"
python3 -I "$W/site/build.py" "$W"
