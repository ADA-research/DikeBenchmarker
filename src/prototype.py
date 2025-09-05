#!/usr/bin/env python3
import asyncio
import logging

import argparse
import os
import sys

import polars as pl

from sustainablecompetition.controller import Controller
from sustainablecompetition.infrastructureadapters.virtual_runner import VirtualRunner
from sustainablecompetition.benchmarkingmethods.trivial_benchmarker import TrivialBenchmarker
from sustainablecompetition.resultconsumers.echo_consumer import EchoConsumer
from sustainablecompetition.dataadapters.competition_dataadapter import CompetitionDataAdapter

logger = logging.getLogger(__name__)


async def main():
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
    runner = VirtualRunner(CompetitionDataAdapter(df))
    benchmarks = df.select("hash").to_series().to_list()
    columns = df.columns
    method = TrivialBenchmarker(benchmarks, columns[1])
    consumer = EchoConsumer()
    controller = Controller(method, runner, njobs=1, consumers=[consumer])
    await controller.run()


if __name__ == "__main__":
    asyncio.run(main())
