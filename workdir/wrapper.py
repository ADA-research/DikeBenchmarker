#!/usr/bin/env python3
# -*- coding: UTF-8 -*-


import re
import subprocess
from pathlib import Path
import argparse

parser = argparse.ArgumentParser(description="sum the integers at the command line")
parser.add_argument("--cutoff", type=int, help="cutoff cpu time")
parser.add_argument("--memory", type=int, help="available memory")
parser.add_argument("--solver", help="the executable of the solver")
parser.add_argument("--instance", help="the instance")
args = parser.parse_args()
# Extract and delete data that needs specific formatting
solver = Path(args.solver)
memory = args.memory
instance = Path(args.instance)
cutoff = args.cutoff


solver_cmd = ["./runsolver", "-C", str(cutoff), "-M", str(memory), str(solver), str(instance)]

# Construct call from args dictionary
try:
    solver_call = subprocess.run(solver_cmd, capture_output=True)
except Exception as ex:
    print(f"Solver call failed with exception:\n{ex}")

# Convert Solver output to dictionary for configurator target algorithm script
output_str = solver_call.stdout.decode()
# Optional: Print original output so the solution can be verified by SolutionVerifier

status = "CRASHED"
if output_str.find("Maximum CPU time exceeded")>-1:
    status = "TIMEOUT"
elif output_str.find("Maximum VSize exceeded")> -1:
    status = "MEMOUT"
elif output_str.find("UNSATISFIABLE")> -1:
    status= "UNSAT"
elif output_str.find("SATISFIABLE")>-1:
    status="SAT"

try:
    rtime = re.search(r"total CPU time \(s\): (\d+\.\d+)", output_str).group(1)
except IndexError:
    rtime = 0

outdir = {"status": status, "quality": rtime, "solver_call": solver_cmd}

print(",".join([status, rtime]))

