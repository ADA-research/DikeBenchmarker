#!/bin/bash
# Configure Git filters for SQLite dump/restore
git config filter.dumpsql.clean 'tmp=$(mktemp); cat > $tmp; sqlite3 $tmp .dump; rm $tmp'
git config filter.dumpsql.smudge 'tmp=$(mktemp); sqlite3 $tmp; cat $tmp; rm $tmp'

# Trigger the smudge filter to restore the database
git checkout -- src/sustainablecompetition/data/sustainablecompetition.db
