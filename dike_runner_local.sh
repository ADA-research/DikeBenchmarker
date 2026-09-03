#!/bin/bash
# Generic local runner for the dike benchmarking manager (no SLURM/sbatch).
# Adjust the variables below, then run: bash dike_runner_local.sh <config.yml> <output-dir>

set -eu

if [[ $# -lt 2 ]]; then
    echo "Usage: $0 <config.yml> <output-dir>" >&2
    exit 1
fi
DIKE_CONFIG=$(readlink -f "$1")
DIKE_OUT=$(readlink -f "$2")

# path to the virtual environment in which Dike is installed
DIKE_VENV=/home/iser/git/dike/code/.venv/bin/activate
# path to the root directory containing instances/, solvers/, etc.
DIKE_DATA_ROOT=/home/iser/git/dike/code/

export PYTHONNOUSERSITE=1
export PYTHONUNBUFFERED=1
source "$DIKE_VENV"

exec dike "$DIKE_DATA_ROOT" "$DIKE_CONFIG" "$DIKE_OUT"
