import argparse
import csv
import importlib.resources
import logging
import os
import sqlite3
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from tqdm import tqdm
from DikeBenchmarker.benchmarkingmethods.benchmarker import Benchmarker
from DikeBenchmarker.benchmarkingmethods.instance_selectors.discrimination_instance_selector import DiscriminationInstanceSelector
from DikeBenchmarker.benchmarkingmethods.instance_selectors.random_instance_selector import RandomInstanceSelector
from DikeBenchmarker.benchmarkingmethods.instance_selectors.variance_instance_selector import VarianceInstanceSelector
from DikeBenchmarker.benchmarkingmethods.stopping_criterion.minimum_accuracy_stopping_criterion import MinimumAccuracyStoppingCriterion
from DikeBenchmarker.benchmarkingmethods.stopping_criterion.percentage_stopping_criterion import PercentageStoppingCriterion
from DikeBenchmarker.benchmarkingmethods.stopping_criterion.wilcoxon_stopping_criterion import WilcoxonStoppingCriterion
from DikeBenchmarker.dataadaptors.dataadaptor import DataAdaptor
from DikeBenchmarker.dataadaptors.inmemory_dataadaptor import InMemoryDataAdaptor
from DikeBenchmarker.dataadaptors.sqlite_dataadaptor import SqlDataAdaptor
from DikeBenchmarker.infrastructureadaptors.abstract_runner import AbstractRunner
from DikeBenchmarker.infrastructureadaptors.virtual_runner import VirtualRunner


INSTANCE_SELECTOR_CLASSES = [VarianceInstanceSelector, RandomInstanceSelector, DiscriminationInstanceSelector]
STOPPING_CRITERION_CLASSES = [MinimumAccuracyStoppingCriterion, WilcoxonStoppingCriterion, PercentageStoppingCriterion]


def _make_selector(cls, bench_ids, solver_id, adap):
    if cls is RandomInstanceSelector:
        return cls(bench_ids, solver_id)
    return cls(bench_ids, solver_id, adap)


def _make_stopping_criterion(cls, benchmark_ids, solver_id, solvers_challenged, confidence, adap):
    if cls is MinimumAccuracyStoppingCriterion:
        return cls(benchmark_ids, [solver_id] + solvers_challenged, confidence, db_adaptor=adap)
    elif cls is PercentageStoppingCriterion:
        return cls(benchmark_ids, 0.2)
    return cls(benchmark_ids, solver_id, solvers_challenged, confidence, db_adaptor=adap)


def generate_all_method_configs():
    """Returns a list of (selector_class, stopping_criterion_class) tuples."""
    return [(sel_cls, stop_cls) for sel_cls in INSTANCE_SELECTOR_CLASSES for stop_cls in STOPPING_CRITERION_CLASSES]


def make_benchmarker_from_config(sel_cls, stop_cls, benchmark_ids, solver_id, solvers_challenged, adap, confidence, checker_id="none"):
    selector = _make_selector(sel_cls, benchmark_ids, solver_id, adap)
    stopping_criteria = _make_stopping_criterion(stop_cls, benchmark_ids, solver_id, solvers_challenged, confidence, adap)
    return Benchmarker(selector, stopping_criteria, benchmark_ids, solver_id, checker_id)


def _run_single_experiment(
    solver_id,
    method_idx,
    sel_cls,
    stop_cls,
    solver_hashes,
    benchmark_ids,
    cost_lookup,
    total_cost_per_solver,
    original_rank_of,
    confidence,
):
    other_solvers = [s for s in solver_hashes if s != solver_id]
    total_cost = total_cost_per_solver[solver_id]

    adaptor = InMemoryDataAdaptor(cost_lookup)

    benchmarker = make_benchmarker_from_config(
        sel_cls,
        stop_cls,
        benchmark_ids=benchmark_ids,
        solver_id=solver_id,
        solvers_challenged=other_solvers,
        adap=adaptor,
        confidence=confidence,
    )

    runner = make_runner(adaptor)
    runner.run([benchmarker])

    # Compute actual cost: sum of runtimes for instances that were actually run
    instances_run = benchmarker.selector.jobs_submitted
    actual_cost = sum(cost_lookup[(inst_id, solver_id)] for inst_id in instances_run)

    # Compute ranking based on only the instances that were run
    subset_cost_per_solver = {s: sum(cost_lookup[(inst_id, s)] for inst_id in instances_run) for s in solver_hashes}
    subset_ranking = sorted(solver_hashes, key=lambda s: subset_cost_per_solver[s])
    subset_rank_of = {s: rank + 1 for rank, s in enumerate(subset_ranking)}

    return [
        solver_id,
        method_idx + 1,
        f"{total_cost:.4f}",
        f"{actual_cost:.4f}",
        len(instances_run),
        len(benchmark_ids),
        f"{actual_cost / total_cost:.4f}" if total_cost > 0 else "0.0000",
        original_rank_of[solver_id],
        subset_rank_of[solver_id],
        len(solver_hashes),
    ]


def make_adaptor() -> SqlDataAdaptor:
    db_path = str(importlib.resources.files("DikeBenchmarker.data.db").joinpath("sustainablecompetition.db"))
    return SqlDataAdaptor(db_path)


def make_runner(adaptor: DataAdaptor) -> AbstractRunner:
    return VirtualRunner(adaptor)


def get_competition_data(adaptor: SqlDataAdaptor, competition: str):
    """Get solver hashes and instance hashes for a competition.

    Returns only instances that have performance data for ALL solvers.
    """
    all_solver_hashes = adaptor.get_competition_solver_id(competition)
    print(f"Competition '{competition}': {len(all_solver_hashes)} registered solvers")

    # Get instances covered by all solvers that have performance data
    conn = sqlite3.connect(adaptor.database_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT p.inst_hash
        FROM performances p
        JOIN solvers s ON p.solver_id = s.solver_id
        WHERE s.competition = ?
        GROUP BY p.inst_hash
        HAVING COUNT(DISTINCT p.solver_id) = (
            SELECT COUNT(DISTINCT p2.solver_id)
            FROM performances p2
            JOIN solvers s2 ON p2.solver_id = s2.solver_id
            WHERE s2.competition = ?
        )
        """,
        (competition, competition),
    )
    benchmark_ids = [row[0] for row in cursor.fetchall()]

    # Only keep solvers that actually have performance data
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT DISTINCT p.solver_id
        FROM performances p
        JOIN solvers s ON p.solver_id = s.solver_id
        WHERE s.competition = ?
        """,
        (competition,),
    )
    solvers_with_data = {row[0] for row in cursor.fetchall()}
    conn.close()

    solver_hashes = [s for s in all_solver_hashes if s in solvers_with_data]
    skipped = len(all_solver_hashes) - len(solver_hashes)
    if skipped:
        print(f"Skipped {skipped} solver(s) with no performance data")
    print(f"Active solvers: {len(solver_hashes)}")
    print(f"Instances with full solver coverage: {len(benchmark_ids)}")
    return solver_hashes, benchmark_ids


CSV_HEADER = [
    "solver_id",
    "method_idx",
    "total_cost",
    "actual_cost",
    "instances_run",
    "total_instances",
    "cost_ratio",
    "original_rank",
    "subset_rank",
    "num_solvers",
    "rank_diff",
]


def load_completed(csv_path: str) -> set[tuple[str, int]]:
    """Load already-completed (solver_id, method_idx) pairs from an existing CSV."""
    completed = set()
    if not os.path.exists(csv_path):
        return completed
    with open(csv_path, "r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            completed.add((row["solver_id"], int(row["method_idx"])))
    return completed


def run_experiment(competition: str, confidence: float, output_dir: str, force: bool = False):
    adaptor = make_adaptor()
    solver_hashes, benchmark_ids = get_competition_data(adaptor, competition)
    method_configs = generate_all_method_configs()

    os.makedirs(output_dir, exist_ok=True)

    # Precompute runtime cost per (instance, solver) pair in one bulk SQL query
    print("Bulk-loading performance data...")
    cost_lookup = adaptor.bulk_load_performances(benchmark_ids, solver_hashes)

    # Precompute total cost per solver (if all benchmarks were run)
    total_cost_per_solver = {}
    for solver_id in solver_hashes:
        total_cost_per_solver[solver_id] = sum(cost_lookup[(inst_id, solver_id)] for inst_id in benchmark_ids)

    # Compute original ranking based on all instances (lower total runtime = better rank)
    original_ranking = sorted(solver_hashes, key=lambda s: total_cost_per_solver[s])
    original_rank_of = {s: rank + 1 for rank, s in enumerate(original_ranking)}

    csv_path = os.path.join(output_dir, f"experiment_results_{competition}.csv")

    # Load already-completed pairs to allow resuming (unless --force)
    completed = set() if force else load_completed(csv_path)
    if completed:
        print(f"Resuming: {len(completed)} experiments already completed, skipping them.")

    # Open in append mode if resuming, otherwise write mode with header
    file_exists = os.path.exists(csv_path) and len(completed) > 0
    csv_file = open(csv_path, "a" if file_exists else "w", newline="")
    csv_writer = csv.writer(csv_file)
    if not file_exists:
        csv_writer.writerow(CSV_HEADER)

    total_iterations = len(solver_hashes) * len(method_configs)
    skipped = len(completed)
    pbar = tqdm(total=total_iterations, initial=skipped, desc="Running experiments")

    # Build list of tasks to run
    tasks = []
    for solver_id in solver_hashes:
        for method_idx, (sel_cls, stop_cls) in enumerate(method_configs):
            if (solver_id, method_idx + 1) in completed:
                continue
            tasks.append((solver_id, method_idx, sel_cls, stop_cls))

    num_workers = min(os.cpu_count() or 1, len(tasks))
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = {
            executor.submit(
                _run_single_experiment,
                sid,
                midx,
                sel_cls,
                stop_cls,
                solver_hashes,
                benchmark_ids,
                cost_lookup,
                total_cost_per_solver,
                original_rank_of,
                confidence,
            ): (sid, midx)
            for sid, midx, sel_cls, stop_cls in tasks
        }
        for future in as_completed(futures):
            row = future.result()
            csv_writer.writerow(row)
            csv_file.flush()
            pbar.update(1)

    pbar.close()
    csv_file.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--competition", type=str, default="main2023")
    parser.add_argument("--confidence", type=float, default=0.95)
    parser.add_argument("--output-dir", type=str, default="results")
    parser.add_argument("-f", "--force", action="store_true", help="Force rewrite, ignoring previous results")
    parser.add_argument(
        "--log-level",
        type=str,
        default="WARNING",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level (default: WARNING)",
    )
    args = parser.parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level))
    run_experiment(args.competition, args.confidence, args.output_dir, args.force)
