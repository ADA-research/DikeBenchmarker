"""Stopping criterion that stops when a minimum ranking accuracy is reached with a Wilcoxon test."""

import warnings

from sustainablecompetition.benchmarkatoms import Result
from sustainablecompetition.benchmarkingmethods.stopping_criterion.stopping_criteria import StoppingCriteria
from sustainablecompetition.dataadaptors.dataadaptor import DataAdaptor

from scipy.stats import wilcoxon

__all__ = ["WilcoxonStoppingCriterion"]


class WilcoxonStoppingCriterion(StoppingCriteria):
    """Stopping criterion that stops when a minimum ranking accuracy is reached with a Wilcoxon test."""

    def __init__(
        self, benchmark_ids: list[str], challenger_id: str, solvers_challenged: list[str], min_accuracy: float, db_adaptor: DataAdaptor, min_instances: int = 5
    ):
        super().__init__()
        self.benchmark_ids = benchmark_ids
        self.min_accuracy = min_accuracy
        self.min_instances = min_instances
        self.selected_benchmark_ids = []
        self.db_adaptor = db_adaptor

        self.challenger = challenger_id

        ## SORT SOLVERS

        # Filter out benchmark instances where any solver has no performance data
        valid_benchmark_ids = []
        for benchmark_id in self.selected_benchmark_ids:
            all_have_perf = True
            for solver_id in solvers_challenged:
                perf_col = self.db_adaptor.get_performances(solver_id=solver_id, inst_hash=benchmark_id).get_column("perf")
                if len(perf_col) == 0:
                    all_have_perf = False
                    break
            if all_have_perf:
                valid_benchmark_ids.append(benchmark_id)
        performances = [
            (
                solver_id,
                sum(
                    [
                        self.db_adaptor.get_performances(solver_id=solver_id, inst_hash=benchmark_id).get_column("perf")[0]
                        for benchmark_id in valid_benchmark_ids
                    ]
                ),
            )
            for solver_id in solvers_challenged
        ]
        sorted_solvers = sorted(performances, key=lambda x: x[1])
        self.sorted_solver_ids = [solver_id for solver_id, _ in sorted_solvers]

    def should_stop(self) -> bool:
        if len(self.selected_benchmark_ids) == 0 or len(self.selected_benchmark_ids) < self.min_instances:
            return False

        # Filter out benchmark instances where any solver has no performance data
        valid_benchmark_ids = []
        for benchmark_id in self.selected_benchmark_ids:
            all_have_perf = True
            for solver_id in self.sorted_solver_ids + [self.challenger]:
                perf_col = self.db_adaptor.get_performances(solver_id=solver_id, inst_hash=benchmark_id).get_column("perf")
                if len(perf_col) == 0:
                    all_have_perf = False
                    break
            if all_have_perf:
                valid_benchmark_ids.append(benchmark_id)

        if len(valid_benchmark_ids) < self.min_instances:
            return False

        my_challenger_perfs = [
            self.db_adaptor.get_performances(solver_id=self.challenger, inst_hash=benchmark_id).get_column("perf")[0] for benchmark_id in valid_benchmark_ids
        ]
        has_progressed = True
        with warnings.catch_warnings():
            warnings.simplefilter(action="ignore", category=UserWarning)
            while has_progressed:
                if len(self.sorted_solver_ids) == 0:
                    return True
                has_progressed = False
                to_compare = self.sorted_solver_ids.pop()
                perfs = [
                    self.db_adaptor.get_performances(solver_id=to_compare, inst_hash=benchmark_id).get_column("perf")[0] for benchmark_id in valid_benchmark_ids
                ]
                _, p_stop = wilcoxon(my_challenger_perfs, perfs, alternative="two-sided")
                if 1 - p_stop >= self.min_accuracy:
                    # Take a decision
                    challenger_is_better = sum(my_challenger_perfs) < sum(perfs)
                    if challenger_is_better:
                        # Go to the next challenger
                        has_progressed = True
                    else:
                        # We are definitively worse
                        return False
                else:
                    # Indecisive
                    self.sorted_solver_ids.append(to_compare)

        return False

    def handle_result(self, result: Result) -> None:
        self.selected_benchmark_ids.append(result.job.benchmark_id)
