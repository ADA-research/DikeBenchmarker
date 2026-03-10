#!/usr/bin/env python3
"""Dike Benchmarker - Main entry point for running benchmarking experiments."""

import argparse
import importlib
import os
import sys
import yaml

from parsl.config import Config
from parsl import HighThroughputExecutor
from parsl.providers import LocalProvider

import polars as pl

from DikeBenchmarker.benchmarkingmethods.benchmarker import Benchmarker
from DikeBenchmarker.benchmarkingmethods.stopping_criterion.stopping_criteria import NoStoppingCriteria
from DikeBenchmarker.benchmarkingmethods.instance_selectors.trivial_instance_selector import TrivialInstanceSelector
from DikeBenchmarker.benchmarkingmethods.instance_selectors.discrimination_instance_selector import DiscriminationInstanceSelector
from DikeBenchmarker.benchmarkingmethods.instance_selectors.random_instance_selector import RandomInstanceSelector
from DikeBenchmarker.benchmarkingmethods.instance_selectors.variance_instance_selector import VarianceInstanceSelector
from DikeBenchmarker.benchmarkingmethods.stopping_criterion.minimum_accuracy_stopping_criterion import MinimumAccuracyStoppingCriterion
from DikeBenchmarker.benchmarkingmethods.stopping_criterion.percentage_stopping_criterion import PercentageStoppingCriterion
from DikeBenchmarker.benchmarkingmethods.stopping_criterion.wilcoxon_stopping_criterion import WilcoxonStoppingCriterion
from DikeBenchmarker.dataadaptors.sqlite_dataadaptor import SqlDataAdaptor
from DikeBenchmarker.infrastructureadaptors.util import slurm_limits

from DikeBenchmarker.infrastructureadaptors.util.parsl_configs import make_slurm_config
from DikeBenchmarker.infrastructureadaptors.parsl_runner import ParslRunner
from DikeBenchmarker.resultconsumers.lambda_consumer import LambdaConsumer
from DikeBenchmarker.solveradaptors.executionwrapper import ExecutionWrapper
from DikeBenchmarker.solveradaptors.solveradaptor import SolverAdaptor
from DikeBenchmarker.benchmarkadaptors.satinstance import SATInstanceAdaptor
from DikeBenchmarker.infrastructureadaptors.util import control


def get_solver_adaptor(solvers_csv: str) -> SolverAdaptor:
    """Create a SolverAdaptor from a CSV file."""
    solver_adaptor = SolverAdaptor()
    solver_adaptor.read_registry(solvers_csv)
    return solver_adaptor


def get_instance_adaptor() -> SATInstanceAdaptor:
    """Create a SATInstanceAdaptor with default paths."""
    instance_adaptor = SATInstanceAdaptor("./instances/sat/", "./instances/cnf_data.db")
    return instance_adaptor


def get_benchmarker(benchmarking_method: dict, solver_id: str, checker_id: str, logroot) -> Benchmarker:
    """Create a benchmarker based on the benchmarking method specified in the configuration."""
    # Base case: if selection method is allpairs, we can use the trivial benchmarker which evaluates
    # all pairs of solvers and instances without any stopping criterion
    if benchmarking_method["selection_method"] == "allpairs":
        return Benchmarker(
            selector=TrivialInstanceSelector(benchmark_ids=benchmarking_method["benchmarks"], solver_id=solver_id),
            stopping_criteria=NoStoppingCriteria(),
            benchmark_ids=benchmarking_method["benchmarks"],
            solver_id=solver_id,
            checker_id=checker_id,
            logroot=logroot,
        )

    # Init data adaptor for selection methods that require performance data (discrimination-based and variance-based) and instance ordering based on that data
    db_path = importlib.resources.files("DikeBenchmarker.data.db").joinpath("sustainablecompetition.db")
    data_adaptor = SqlDataAdaptor(db_path)

    benchmark_ids = benchmarking_method["benchmarks"]
    solvers = data_adaptor.get_solvers_covering_instances(benchmark_ids)

    # For other selection methods, we need to create the appropriate instance selector and stopping criterion based on the configuration
    if benchmarking_method["stopping_criterion"] == "minimum-accuracy":
        stopping_criterion = MinimumAccuracyStoppingCriterion(benchmark_ids, solvers, min_accuracy=benchmarking_method["stopping_threshold"], data=data_adaptor)
    elif benchmarking_method["stopping_criterion"] == "percentage":
        stopping_criterion = PercentageStoppingCriterion(benchmark_ids, percentage=benchmarking_method["stopping_threshold"])
    elif benchmarking_method["stopping_criterion"] == "wilcoxon":
        stopping_criterion = WilcoxonStoppingCriterion(
            benchmark_ids,
            solver_id,
            solvers,
            min_accuracy=benchmarking_method["stopping_threshold"],
            db_adaptor=data_adaptor,
            min_instances=5,
        )
    else:
        stopping_criterion = PercentageStoppingCriterion(benchmark_ids, percentage=1.0)  # No stopping, evaluate all selected instances

    if benchmarking_method["selection_method"] == "random":
        selector = RandomInstanceSelector(benchmark_ids, solver_id)  # TODO: add seed to config
    elif benchmarking_method["selection_method"] == "discrimination-based":
        selector = DiscriminationInstanceSelector(benchmark_ids, solver_id, data_adaptor)  # TODO: add rho to config
    elif benchmarking_method["selection_method"] == "variance-based":
        selector = VarianceInstanceSelector(benchmark_ids, solver_id, data_adaptor)  # TODO: add parameters to config
    else:
        raise ValueError(f"Unsupported selection method: {benchmarking_method['selection_method']}")

    return Benchmarker(
        selector=selector,
        stopping_criteria=stopping_criterion,
        benchmark_ids=benchmark_ids,
        solver_id=solver_id,
        checker_id=checker_id,
        logroot=logroot,
    )


def run_slurm(
    benchmarking_method: dict,
    solvers_file: str,
    resource_limits: dict,
    logroot,
    machine: str,
    account: str = None,
    tasks_per_node: int = 32,
    jobname: str = "benchmark",
    workerinit: str = "",
    queuelimit: int = None,
):
    """Run trivial benchmarking method on slurm cluster."""
    print(f"Benchmarking solvers in {solvers_file}")
    print(
        f"Using {len(benchmarking_method['benchmarks'])} benchmarks, "
        f"selection method {benchmarking_method['selection_method']}, "
        f"stopping criterion {benchmarking_method['stopping_criterion']} "
        f"with threshold {benchmarking_method['stopping_threshold']}"
    )
    print(f"Using machine {machine} with account {account} and {tasks_per_node} tasks per node.")

    solver_adaptor = get_solver_adaptor(solvers_file)
    instance_adaptor = get_instance_adaptor()

    queue_max = queuelimit or slurm_limits.compute_max_blocks(safety_factor=0.8, fallback=100)

    config = make_slurm_config(
        partition=machine,
        account=account,
        jobname=jobname,
        tasks_per_node=tasks_per_node,
        walltime_seconds=resource_limits["solver_walltime"] + resource_limits["checker_walltime"],
        max_blocks=queue_max,
        worker_init=workerinit,
    )

    methods = []
    for sid in solver_adaptor.get_ids():
        method = get_benchmarker(benchmarking_method, sid, checker_id=solver_adaptor.get_checker(sid), logroot=logroot)
        method.register_consumer(LambdaConsumer(print))
        methods.append(method)

    runner = ParslRunner(
        solver_adaptor=solver_adaptor,
        instance_adaptor=instance_adaptor,
        solver_wrapper=ExecutionWrapper(
            cputime=resource_limits["solver_cputime"], walltime=resource_limits["solver_walltime"], mem=resource_limits["solver_memory"]
        ),
        checker_wrapper=ExecutionWrapper(
            cputime=resource_limits["checker_cputime"], walltime=resource_limits["checker_walltime"], mem=resource_limits["checker_memory"]
        ),
        parsl_config=config,
    )

    runner.run(methods, njobs=queue_max * tasks_per_node)


def run_local(
    benchmarking_method: dict,
    solvers_file: str,
    resource_limits: dict,
    logroot,
    parallel: int = 3,
    jobname: str = "benchmark",
):
    """Run trivial benchmarking method on local machine."""
    print(f"Benchmarking solvers in {solvers_file}")
    print(
        f"Using {len(benchmarking_method['benchmarks'])} benchmarks, "
        f"selection method {benchmarking_method['selection_method']}, "
        f"stopping criterion {benchmarking_method['stopping_criterion']} "
        f"with threshold {benchmarking_method['stopping_threshold']}"
    )
    print(f"Using local execution with {parallel} parallel workers.")

    solver_adaptor = get_solver_adaptor(solvers_file)
    instance_adaptor = get_instance_adaptor()

    config = Config(executors=[HighThroughputExecutor(label=jobname, max_workers_per_node=parallel, provider=LocalProvider())])

    methods = []
    for sid in solver_adaptor.get_ids():
        method = get_benchmarker(benchmarking_method, sid, checker_id=solver_adaptor.get_checker(sid), logroot=logroot)
        method.register_consumer(LambdaConsumer(print))
        methods.append(method)

    runner = ParslRunner(
        solver_adaptor=solver_adaptor,
        instance_adaptor=instance_adaptor,
        solver_wrapper=ExecutionWrapper(
            cputime=resource_limits["solver_cputime"], walltime=resource_limits["solver_walltime"], mem=resource_limits["solver_memory"]
        ),
        checker_wrapper=ExecutionWrapper(
            cputime=resource_limits["checker_cputime"], walltime=resource_limits["checker_walltime"], mem=resource_limits["checker_memory"]
        ),
        parsl_config=config,
    )

    runner.run(methods, njobs=parallel * 2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Dike: Data-Informed Knowledge-driven Evaluation")

    parser.add_argument("config", type=str, help="Path to YAML configuration file")
    parser.add_argument("--requeue", type=str, default=None, help="Path to slurm script for requeuing; if not provided then requeuing is disabled.")

    args = parser.parse_args()

    if args.requeue:
        control.set_slurm_requeue_script_path(args.requeue)

    # Load configuration from YAML file
    try:
        with open(args.config, "r") as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        print(f"Error: Configuration file '{args.config}' not found.")
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"Error: Failed to parse YAML configuration: {e}")
        sys.exit(1)

    # Get the directory containing the config file
    config_dir = os.path.dirname(os.path.abspath(args.config))

    # Load benchmarks from CSV
    benchmarking = config.get("benchmarks", {})
    benchmarks_file = os.path.join(config_dir, benchmarking.get("file", ""))

    if not benchmarks_file or not os.path.isfile(benchmarks_file):
        print(f"Error: Benchmarks file '{benchmarks_file}' not found.")
        sys.exit(1)

    benchmarking_method = {
        "benchmarks": pl.read_csv(benchmarks_file).select("hash").to_series().to_list(),
        "selection_method": benchmarking.get("selection_method", "allpairs"),
        "stopping_criterion": benchmarking.get("stopping_criterion", "none"),
        "stopping_threshold": benchmarking.get("stopping_threshold", 0.0),
    }

    # Load solvers file
    solvers_file = os.path.join(config_dir, config.get("solvers"))
    if not solvers_file or not os.path.isfile(solvers_file):
        print(f"Error: Solvers file '{solvers_file}' not found.")
        sys.exit(1)

    # Extract resource limits from configuration
    resource_limits = {
        "solver_cputime": config.get("solver_cputime", 5000),
        "solver_walltime": config.get("solver_walltime", 7000),
        "solver_memory": config.get("solver_memory", 64 * 1024),
        "checker_cputime": config.get("checker_cputime", 45000),
        "checker_walltime": config.get("checker_walltime", 70000),
        "checker_memory": config.get("checker_memory", 64 * 1024),
    }

    # Output directory for logs and results
    results = os.path.join(config_dir, config.get("results"))

    scheduling = config.get("scheduling", {})
    scheduler = scheduling.get("scheduler", "slurm")

    if scheduler == "slurm":
        print("Running with SLURM scheduler...")

        control.register_shutdown_handler()

        run_slurm(
            benchmarking_method=benchmarking_method,
            solvers_file=solvers_file,
            resource_limits=resource_limits,
            logroot=results,
            machine=scheduling.get("machine"),
            account=scheduling.get("account"),
            tasks_per_node=scheduling.get("tasks_per_node", 32),
            jobname=scheduling.get("jobname", "benchmark"),
            workerinit=scheduling.get("workerinit", ""),
            queuelimit=scheduling.get("queuelimit", None),
        )
    elif scheduler == "local":
        print("Running with local scheduler...")

        control.register_shutdown_handler()

        run_local(
            benchmarking_method=benchmarking_method,
            solvers_file=solvers_file,
            resource_limits=resource_limits,
            logroot=results,
            parallel=scheduling.get("parallel", 3),
            jobname=scheduling.get("jobname", "benchmark"),
        )
    else:
        print(f"Error: Unsupported scheduler '{scheduler}'.")
        sys.exit(1)
