#!/bin/bash
# Generic SLURM runner for submitting the dike benchmarking manager.
# Adjust the variables below and the #SBATCH resource directives, 
# then submit with: sbatch dike_runner_slurm.sh <config.yml> <output-dir>

#SBATCH --job-name=dike-run
#SBATCH --output=dike-run-%j.log
#SBATCH --error=dike-run-%j.log
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --signal=B:USR1@300             # warning before walltime, for graceful shutdown of the manager job
#SBATCH --time=3-00:00:00               # maximal time limit for manager; self-requeues on USR1 if it needs more

# Uncomment and adapt as needed for your cluster:
# #SBATCH --partition=cpuonly
# #SBATCH --account=hk-project-p0027597
# #SBATCH --reservation=sat2

set -eu

if [[ $# -lt 2 ]]; then
    echo "Usage: $0 <config.yml> <output-dir>" >&2
    exit 1
fi
DIKE_CONFIG=$(readlink -f "$1")
DIKE_OUT=$(readlink -f "$2")

# path to the virtual environment in which Dike is installed
DIKE_VENV=/path/to/venv/bin/activate
# path to the root directory containing instances/, solvers/, etc.
DIKE_DATA_ROOT=/path/to/data

# Resolve own path so dike can resubmit a continuation job on walltime warning.
REQUEUE_SCRIPT=$(readlink -f "$0")

export PYTHONNOUSERSITE=1
export PYTHONUNBUFFERED=1
source "$DIKE_VENV"

exec dike "$DIKE_DATA_ROOT" "$DIKE_CONFIG" "$DIKE_OUT" --requeue "$REQUEUE_SCRIPT"
