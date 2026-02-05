#!/bin/bash

#SBATCH --job-name=parsl-master
#SBATCH --output=parsl-master-%j.out
#SBATCH --error=parsl-master-%j.err
#SBATCH --time=00:30:00                 # total walltime
#SBATCH --signal=B:USR1@600             # 10 min warning before end
#SBATCH --requeue                       # allow automatic requeue if preempted
#SBATCH --partition=cook                # name of slurm partition to use for the master job
#SBATCH --nodes=1                       # only one node
#SBATCH --ntasks=1                      # single task (process)
#SBATCH --cpus-per-task=1               # single core
#SBATCH --mem=2G                        # minimal memory

source ./venv/bin/activate

./src/nemesis.py ./config/satcomp25micro2.yml
