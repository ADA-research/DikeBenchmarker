#!/bin/bash
# SC2026 quick-test SLURM submission script.
# Run from the dike/ directory:  sbatch sc2026quick.slurm.sh

#SBATCH --job-name=parsl-main
#SBATCH --output=parsl-main-%j.log
#SBATCH --error=parsl-main-%j.log
#SBATCH --signal=B:USR1@300             # 5 min warning before end
#SBATCH --time=12:00:00                 # 33 solvers x 20 instances, ~12h budget
#SBATCH --partition=cpuonly
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1

DIKE_DIR=/home/hk-project-toolbox/fv2117/git/sc2026/dike
VENV=/home/hk-project-toolbox/fv2117/git/sc2026/venv/bin/activate

cd "$DIKE_DIR"

export PYTHONNOUSERSITE=1
export PYTHONUNBUFFERED=1
source "$VENV"

# 'exec' lets SLURM signals (SIGUSR1) reach the Python process directly,
# enabling graceful shutdown and requeue.
exec python ./src/dike.py ./config/sc2026quick.slurm.yml \
    --requeue "$SLURM_SUBMIT_DIR/sc2026quick.slurm.sh"
