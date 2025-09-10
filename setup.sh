#!/bin/bash
# Configure Git filters for SQLite dump/restore
git config filter.dumpsql.clean 'sqlite3 %f ".dump" > data/dump.sql'
git config filter.dumpsql.smudge 'cat data/dump.sql | sqlite3 %f'

# Trigger the smudge filter to restore the database
git checkout -- data/sustainablecompetition.db