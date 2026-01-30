#!/usr/bin/env python3

"""A prototype integration test using the virtual runner and the parsl runner."""

import logging

import argparse
import os
import sys

import polars as pl

from sustainablecompetition.infrastructureadaptors import slurm_limits

from sustainablecompetition.infrastructureadaptors.parsl_configs import make_local_processes, make_slurm_config
from sustainablecompetition.infrastructureadaptors.virtual_runner import VirtualRunner
from sustainablecompetition.infrastructureadaptors.parsl_runner import ParslRunner
from sustainablecompetition.benchmarkingmethods.trivial_benchmarker import TrivialBenchmarker
from sustainablecompetition.resultconsumers.csv_consumer import CSVConsumer
from sustainablecompetition.resultconsumers.lambda_consumer import LambdaConsumer
from sustainablecompetition.dataadaptors.competition_dataadaptor import CompetitionDataAdaptor
from sustainablecompetition.solveradaptors.executionwrapper import ExecutionWrapper
from sustainablecompetition.solveradaptors.solveradaptor import SolverAdaptor
from sustainablecompetition.benchmarkadaptors.satinstance import SATInstanceAdaptor

logger = logging.getLogger(__name__)

short_easybatch = [
    "005ccb378ced61c02105ed7ee0a62038",
    "00f969737ba4338bd233cd3ed249bd55",
    "02b69d0e5c2b68d5c3d650164b6c277d",
    "04327b18171b43ff06586707499b97fc",
    "076d4d6f83306ee69c35e3c99e30d8f8",
    "0928111a3d5d5ce05dffb83cb5982eba",
    "0ef68fc7aa6f2bc7fb74ada9d865da06",
]

long_easybatch = short_easybatch + [
    "18f54820956791d3028868b56a09c6cd",
    "1fdc28d676358b7e66bdf072dbbdba0b",
    "23a92c04ee9248308a18d6a44e5d15f0",
    "44092fcc83a5cba81419e82cfd18602c",
    "47e3b78c2157b685e23b53915a1b33b5",
    "988603bd72158a0c8491d29b7c62c04e",
    "c132cafd8ed646965f6786c423623840",
    "db3be4cbdcf663dbd37f6fa58d4f6bce",
    "e49c408c713af6dde16f707e38419a3c",
    "f349621e75ede4e9e9422b3d0f677268",
    "f42d2ce7b4efd3f96e063dd1f6fec7f1",
]


def virtual_integration_test(simulation_data_csv: str):
    """Integration test using the trivial benchmarker (which submits all the instances) and the virtual runner (which returns the data from a csv file)."""
    df = pl.read_csv(simulation_data_csv)
    runner = VirtualRunner(CompetitionDataAdaptor(df))
    benchmarks = df.select("hash").to_series().to_list()
    solver = df.columns[1]
    method = TrivialBenchmarker(benchmarks, solver, checker_id="dratbin", logroot="./logs")
    method.register_consumer(LambdaConsumer(print))
    runner.run([method], 1)


def create_parsl_runner(
    solver_adaptor,
    instance_adaptor,
    config,
    solver_cputime=5000,
    solver_walltime=7000,
    solver_memory=64 * 1024,
    checker_cputime=45000,
    checker_walltime=70000,
    checker_memory=64 * 1024,
):
    """Create a ParslRunner with SAT solvers and instance adaptors."""
    solver_wrapper = ExecutionWrapper(cputime=solver_cputime, walltime=solver_walltime, mem=solver_memory)
    checker_wrapper = ExecutionWrapper(cputime=checker_cputime, walltime=checker_walltime, mem=checker_memory)
    runner = ParslRunner(
        solver_adaptor=solver_adaptor,
        instance_adaptor=instance_adaptor,
        solver_wrapper=solver_wrapper,
        checker_wrapper=checker_wrapper,
        parsl_config=config,
    )
    return runner


def parsl_local_integration_test(benchmarks):
    """Integration test using the parsl local runner."""
    solver_adaptor = SolverAdaptor()
    solver_adaptor.read_registry("./examples/solverAdaptors/sat/solvers1.csv")
    instance_adaptor = SATInstanceAdaptor("./instances/sat/", "./instances/cnf_data.db")
    config = make_local_processes(3)
    methods = []
    for sid in solver_adaptor.get_ids():
        method = TrivialBenchmarker(benchmarks, sid, checker_id=solver_adaptor.get_checker(sid), logroot="./logs")
        method.register_consumer(LambdaConsumer(print))
        method.register_consumer(CSVConsumer(f"local_test_results_{sid}.csv"))
        methods.append(method)
    runner = create_parsl_runner(solver_adaptor, instance_adaptor, config)
    runner.run(methods, njobs=10)


def parsl_slurm_integration_test(
    benchmarks,
    solvers,
    machine: str,
    account: str = None,
    tasks_per_node: int = 32,
    jobname: str = "benchmark_job",
    solver_cputime: int = 5000,
    solver_walltime: int = 7000,
    solver_memory: int = 64 * 1024,
    checker_cputime: int = 45000,
    checker_walltime: int = 70000,
    checker_memory: int = 64 * 1024,
):
    """Integration test using the parsl slurm runner."""
    solver_adaptor = SolverAdaptor()
    solver_adaptor.read_registry(solvers)
    instance_adaptor = SATInstanceAdaptor("./instances/sat/", "./instances/cnf_data.db")
    walltime_seconds = solver_walltime + checker_walltime + 600  # extra buffer

    queue_max = slurm_limits.compute_max_blocks(safety_factor=0.8, fallback=100)

    config = make_slurm_config(
        partition=machine,
        account=account,  # your account name or None to skip
        jobname=jobname,
        tasks_per_node=tasks_per_node,
        walltime=f"{walltime_seconds // 3600:02d}:{(walltime_seconds % 3600) // 60:02d}:{walltime_seconds % 60:02d}",
        max_blocks=queue_max,
    )
    methods = []
    for sid in solver_adaptor.get_ids():
        method = TrivialBenchmarker(benchmarks, sid, checker_id=solver_adaptor.get_checker(sid), logroot="./logs")
        method.register_consumer(LambdaConsumer(print))
        method.register_consumer(CSVConsumer(f"slurm_test_results_{sid}.csv"))
        methods.append(method)
    runner = create_parsl_runner(
        solver_adaptor, instance_adaptor, config, solver_cputime, solver_walltime, solver_memory, checker_cputime, checker_walltime, checker_memory
    )
    runner.run(methods, njobs=queue_max * tasks_per_node)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test run the benchmarking tool")

    parser.add_argument("--solver_cputime", type=int, default=5000, help="CPU time limit for solvers in seconds")
    parser.add_argument("--solver_walltime", type=int, default=7000, help="Wall time limit for solvers in seconds")
    parser.add_argument("--solver_memory", type=int, default=64 * 1024, help="Memory limit for solvers in MB")
    parser.add_argument("--checker_cputime", type=int, default=45000, help="CPU time limit for checkers in seconds")
    parser.add_argument("--checker_walltime", type=int, default=70000, help="Wall time limit for checkers in seconds")
    parser.add_argument("--checker_memory", type=int, default=64 * 1024, help="Memory limit for checkers in MB")

    subparsers = parser.add_subparsers(dest="command", required=True, help="Execution mode")

    parser_virtual = subparsers.add_parser("virtual", help="Run virtual integration test")
    parser_virtual.add_argument("file", help="Path to CSV file containing solver runtimes")

    parser_local = subparsers.add_parser("local", help="Run local parsl integration test")

    parser_slurm = subparsers.add_parser("slurm", help="Run slurm parsl integration test")
    parser_slurm.add_argument("machine", help="machine/partition name for SLURM")
    parser_slurm.add_argument("--account", help="Account name for SLURM", default=None)
    parser_slurm.add_argument("--tasks-per-node", type=int, help="Number of tasks per node", default=32)
    parser_slurm.add_argument("--jobname", help="Job name for SLURM", default="benchmark")
    parser_slurm.add_argument("--bfile", help="Path to CSV containing benchmark hashes", default=None)
    parser_slurm.add_argument("--sfile", help="Path to CSV containing solver paths", default=None)

    args = parser.parse_args()

    if args.command == "virtual":
        if not os.path.isfile(args.file):
            print(f"Error: File '{args.file}' does not exist.")
            sys.exit(1)
        print("Running virtual integration test...")
        virtual_integration_test(args.file)
    elif args.command == "local":
        print("Running parsl local integration test...")
        parsl_local_integration_test(benchmarks=short_easybatch)
    elif args.command == "slurm":
        print("Running parsl slurm integration test...")

        if args.bfile:
            if not os.path.isfile(args.bfile):
                print(f"Error: File '{args.bfile}' does not exist.")
                sys.exit(1)
            df = pl.read_csv(args.bfile)
            benchmarks = df.select("hash").to_series().to_list()
        else:  # fallback to default
            benchmarks = long_easybatch

        if args.sfile:
            if not os.path.isfile(args.sfile):
                print(f"Error: File '{args.sfile}' does not exist.")
                sys.exit(1)
            solvers = args.sfile
        else:  # fallback to default
            solvers = "./examples/solverAdaptors/sat/solvers1.csv"

        parsl_slurm_integration_test(
            benchmarks=benchmarks,
            solvers=solvers,
            machine=args.machine,
            account=args.account,
            tasks_per_node=args.tasks_per_node,
            jobname=args.jobname,
            solver_cputime=args.solver_cputime,
            solver_walltime=args.solver_walltime,
            solver_memory=args.solver_memory,
            checker_cputime=args.checker_cputime,
            checker_walltime=args.checker_walltime,
            checker_memory=args.checker_memory,
        )
