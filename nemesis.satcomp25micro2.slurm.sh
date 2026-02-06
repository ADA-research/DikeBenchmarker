#!/bin/bash

#SBATCH --job-name=parsl-master
#SBATCH --output=parsl-master-%j.out
#SBATCH --error=parsl-master-%j.err
#SBATCH --signal=B:USR1@300             # 5 min warning before end
#SBATCH --time=00:15:00                 # total walltime
#SBATCH --requeue                       # allow automatic requeue if preempted
#SBATCH --partition=cook                # name of slurm partition to use for the master job
#SBATCH --nodes=1                       # only one node
#SBATCH --ntasks=1                      # single task (process)
#SBATCH --cpus-per-task=1               # single core

SLURM_SCRIPT="$(readlink -f "$0")"

export PYTHONNOUSERSITE=1
source ./venv/bin/activate

./src/nemesis.py ./config/satcomp25micro2.yml --requeue "$SLURM_SCRIPT"
