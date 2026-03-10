#!/bin/bash
# Configure Git filters for SQLite dump/restore
# The .db file can live in a submodule, so configure the filter there
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
git -C "$SCRIPT_DIR" config filter.dumpsql.clean 'tmp=$(mktemp); cat > "$tmp"; sqlite3 "$tmp" .dump; rm "$tmp"'
git -C "$SCRIPT_DIR" config filter.dumpsql.smudge 'tmp=$(mktemp); sqlite3 "$tmp"; cat "$tmp"; rm "$tmp"'

# Force re-checkout to trigger the smudge filter and restore the database
rm -f "$SCRIPT_DIR/sustainablecompetition.db"
git -C "$SCRIPT_DIR" checkout -- sustainablecompetition.db
