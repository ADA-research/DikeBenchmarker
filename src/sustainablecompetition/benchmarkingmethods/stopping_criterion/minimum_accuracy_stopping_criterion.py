"""Stopping criterion that stops when a minimum ranking accuracy is reached."""

from sustainablecompetition.benchmarkatoms import Result
from sustainablecompetition.benchmarkingmethods.stopping_criterion.stopping_criteria import StoppingCriteria
from sustainablecompetition.dataadaptors.dataadaptor import DataAdaptor

__all__ = ["MinimumAccuracyStoppingCriterion"]


class MinimumAccuracyStoppingCriterion(StoppingCriteria):
    """Stopping criterion that stops when a minimum ranking accuracy is reached."""

    def __init__(self, benchmark_ids: list[str], solvers: list[str], min_accuracy: float, db_adaptor: DataAdaptor):
        super().__init__()
        self.benchmark_ids = benchmark_ids
        self.min_accuracy = min_accuracy
        self.selected_benchmark_ids = []
        self.db_adaptor = db_adaptor
        self.solvers = solvers
        self.instance_performances = {}

        # Filter out benchmark instances where any solver has no performance data
        valid_benchmark_ids = []
        for benchmark_id in self.selected_benchmark_ids:
            all_have_perf = True
            for solver_id in self.solvers:
                perf_col = self.db_adaptor.get_performances(solver_hash=solver_id, inst_hash=benchmark_id).get_column("perf")
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
                        self.db_adaptor.get_performances(solver_hash=solver_id, inst_hash=benchmark_id).get_column("perf")[0]
                        for benchmark_id in valid_benchmark_ids
                    ]
                ),
            )
            for solver_id in self.solvers
        ]
        sorted_solvers = sorted(performances, key=lambda x: x[1])
        self.sorted_solver_ids = [solver_id for solver_id, _ in sorted_solvers]

    def should_stop(self) -> bool:
        if len(self.selected_benchmark_ids) == 0:
            return False

        # Stop if all benchmark instances have been run
        if set(self.benchmark_ids).issubset(set(self.selected_benchmark_ids)):
            return True

        total_pairs = len(self.solvers) * (len(self.solvers) - 1) // 2

        # Filter out benchmark instances where any solver has no performance data
        valid_benchmark_ids = []
        for benchmark_id in self.selected_benchmark_ids:
            all_have_perf = True
            for solver_id in self.solvers:
                perf_col = self.db_adaptor.get_performances(solver_hash=solver_id, inst_hash=benchmark_id).get_column("perf")
                if len(perf_col) == 0:
                    all_have_perf = False
                    break
            if all_have_perf:
                valid_benchmark_ids.append(benchmark_id)

        if len(valid_benchmark_ids) <= 0:
            return self.min_accuracy <= 0

        performances = [
            (
                solver_id,
                sum(
                    [
                        self.db_adaptor.get_performances(solver_hash=solver_id, inst_hash=benchmark_id).get_column("perf")[0]
                        for benchmark_id in valid_benchmark_ids
                    ]
                ),
            )
            for solver_id in self.solvers
        ]
        sorted_solvers = sorted(performances, key=lambda x: x[1])
        sorted_solver_ids = [solver_id for solver_id, _ in sorted_solvers]

        correct_pairs = 0
        for i in range(len(self.solvers)):
            for j in range(i + 1, len(self.solvers)):
                solver_i = self.sorted_solver_ids[i]
                solver_j = self.sorted_solver_ids[j]
                idx_i = sorted_solver_ids.index(solver_i)
                idx_j = sorted_solver_ids.index(solver_j)
                if idx_i < idx_j:
                    correct_pairs += 1

        accuracy = correct_pairs / total_pairs
        return accuracy >= self.min_accuracy

    def handle_result(self, result: Result) -> None:
        self.selected_benchmark_ids.append(result.job.benchmark_id)
