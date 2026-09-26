#!/usr/bin/env bash
# Online SQLite backup: safe under WAL, no downtime.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DB="${CHECKPOINT_DB_PATH:-$ROOT/data/checkpoints.db}"
OUT_DIR="${BACKUP_DIR:-$ROOT/data/backups}"
mkdir -p "$OUT_DIR"
if [[ ! -f "$DB" ]]; then
  echo "no db at $DB — nothing to back up" >&2; exit 0
fi
ts="$(date -u +%Y%m%dT%H%M%SZ)"
out="$OUT_DIR/checkpoints-$ts.db"
sqlite3 "$DB" ".backup '$out'"
echo "backup → $out"
ls -lh "$out"
