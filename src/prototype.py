#!/usr/bin/env python3

"""
A prototype integration test using the virtual runner and the parsl runner.
"""

import asyncio
import logging

import argparse
import os
import sys

import polars as pl

from sustainablecompetition.controller import Controller
from sustainablecompetition.infrastructureadaptors.parsl_configs import make_local_processes
from sustainablecompetition.infrastructureadaptors.virtual_runner import VirtualRunner
from sustainablecompetition.infrastructureadaptors.parsl_runner import ParslRunner
from sustainablecompetition.benchmarkingmethods.trivial_benchmarker import TrivialBenchmarker
from sustainablecompetition.resultconsumers.lambda_consumer import LambdaConsumer
from sustainablecompetition.dataadaptors.competition_dataadaptor import CompetitionDataAdaptor
from sustainablecompetition.infrastructureadaptors.executionwrapper import RunSolverWrapper
from sustainablecompetition.solveradaptors.satsolver import SATSolverAdaptor
from sustainablecompetition.benchmarkadaptors.satinstance import SATInstanceAdaptor

logger = logging.getLogger(__name__)


async def virtual_integration_test():
    """
    Integration test using the trivial benchmarker (which submits all the instances)
    and the virtual runner (which returns the data from a csv file).
    """
    parser = argparse.ArgumentParser(description="Test run the benchmarking tool")
    parser.add_argument("file", help="Path to CSV file containing solver runtimes")
    args = parser.parse_args()

    if not os.path.isfile(args.file):
        print(f"Error: File '{args.file}' does not exist.")
        sys.exit(1)

    df = pl.read_csv(args.file)
    runner = VirtualRunner(CompetitionDataAdaptor(df))
    benchmarks = df.select("hash").to_series().to_list()
    columns = df.columns
    method = TrivialBenchmarker(benchmarks, columns[1])
    consumer = LambdaConsumer(print)
    controller = Controller(method, runner, njobs=1, consumers=[consumer])
    await controller.run()


async def parsl_integration_test():
    """
    Integration test using the trivial benchmarker (which submits all the instances)
    and the virtual runner (which returns the data from a csv file).
    """
    parser = argparse.ArgumentParser(description="Test run the benchmarking tool")
    parser.add_argument("file", help="Path to CSV file containing solver runtimes")
    args = parser.parse_args()

    if not os.path.isfile(args.file):
        print(f"Error: File '{args.file}' does not exist.")
        sys.exit(1)

    df = pl.read_csv(args.file)
    # runner = VirtualRunner(CompetitionDataAdaptor(df))
    solver_adaptor = SATSolverAdaptor()
    solver_adaptor.register_solver("kissat", "./examples/solverAdaptors/sat/kissat")  # Update
    runner = ParslRunner(
        rootdir=".",
        solver_adaptor=solver_adaptor,
        instance_adaptor=SATInstanceAdaptor("."),
        execution_wrapper=RunSolverWrapper("."),
        parsl_config=make_local_processes(4),
    )
    benchmarks = df.select("hash").to_series().to_list()
    method = TrivialBenchmarker(benchmarks, "kissat")
    consumer = LambdaConsumer(print)
    controller = Controller(method, runner, njobs=10, consumers=[consumer])
    await controller.run()


if __name__ == "__main__":
    asyncio.run(virtual_integration_test())
    asyncio.run(parsl_integration_test())
