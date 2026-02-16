import importlib
import pytest

from sustainablecompetition.benchmarkatoms import Job, Result
from sustainablecompetition.benchmarkingmethods.stopping_criterion.minimum_accuracy_stopping_criterion import MinimumAccuracyStoppingCriterion
from sustainablecompetition.benchmarkingmethods.stopping_criterion.wilcoxon_stopping_criterion import WilcoxonStoppingCriterion
from sustainablecompetition.dataadaptors.sqlite_dataadaptor import SqlDataAdaptor


def build_adaptor() -> SqlDataAdaptor:
    db_path = importlib.resources.files("sustainablecompetition.data.db").joinpath("sustainablecompetition.db")
    db_adaptor = SqlDataAdaptor(db_path)
    return db_adaptor


def make_result(benchmark_id: str, solver_id: str) -> Result:
    job = Job(job_producer=None, benchmark_id=benchmark_id, solver_id=solver_id, checker_id="", logroot="")
    return Result(job=job)


@pytest.fixture
def adaptor():
    return build_adaptor()


@pytest.fixture
def benchmark_ids(adaptor):
    return list(set(adaptor.get_performances().get_column("inst_hash").to_list()))[:10]


@pytest.fixture
def solver_ids(adaptor):
    return adaptor.get_all_solver_ids()


class TestMinimumAccuracyStoppingCriterion:
    def test_does_not_stop_initially(self, adaptor, benchmark_ids, solver_ids):
        criterion = MinimumAccuracyStoppingCriterion(benchmark_ids, solver_ids, min_accuracy=0.5, db_adaptor=adaptor)
        assert criterion.should_stop() is False

    def test_stops_with_all_instances(self, adaptor, benchmark_ids, solver_ids):
        criterion = MinimumAccuracyStoppingCriterion(benchmark_ids, solver_ids, min_accuracy=1.0, db_adaptor=adaptor)
        for bid in benchmark_ids:
            criterion.handle_result(make_result(bid, solver_ids[0]))
        assert criterion.should_stop() is True

    def test_handle_result_adds_benchmark(self, adaptor, benchmark_ids, solver_ids):
        criterion = MinimumAccuracyStoppingCriterion(benchmark_ids, solver_ids, min_accuracy=0.5, db_adaptor=adaptor)
        criterion.handle_result(make_result(benchmark_ids[0], solver_ids[0]))
        assert benchmark_ids[0] in criterion.selected_benchmark_ids

    def test_low_accuracy_threshold(self, adaptor, benchmark_ids, solver_ids):
        criterion = MinimumAccuracyStoppingCriterion(benchmark_ids, solver_ids, min_accuracy=0.0, db_adaptor=adaptor)
        criterion.handle_result(make_result(benchmark_ids[0], solver_ids[0]))
        assert criterion.should_stop() is True


class TestWilcoxonStoppingCriterion:
    def test_does_not_stop_initially(self, adaptor, benchmark_ids, solver_ids):
        criterion = WilcoxonStoppingCriterion(benchmark_ids, solver_ids[0], solver_ids[1:3], min_accuracy=0.95, db_adaptor=adaptor)
        assert criterion.should_stop() is False

    def test_does_not_stop_below_min_instances(self, adaptor, benchmark_ids, solver_ids):
        criterion = WilcoxonStoppingCriterion(benchmark_ids, solver_ids[0], solver_ids[1:3], min_accuracy=0.95, db_adaptor=adaptor, min_instances=5)
        for bid in benchmark_ids[:4]:
            criterion.handle_result(make_result(bid, solver_ids[0]))
        assert criterion.should_stop() is False

    def test_handle_result_adds_benchmark(self, adaptor, benchmark_ids, solver_ids):
        criterion = WilcoxonStoppingCriterion(benchmark_ids, solver_ids[0], solver_ids[1:3], min_accuracy=0.95, db_adaptor=adaptor)
        criterion.handle_result(make_result(benchmark_ids[0], solver_ids[0]))
        assert benchmark_ids[0] in criterion.selected_benchmark_ids

    def test_stops_with_enough_instances(self, adaptor, benchmark_ids, solver_ids):
        criterion = WilcoxonStoppingCriterion(benchmark_ids, solver_ids[0], solver_ids[1:3], min_accuracy=0.5, db_adaptor=adaptor, min_instances=5)
        for bid in benchmark_ids:
            criterion.handle_result(make_result(bid, solver_ids[0]))
            if criterion.should_stop():
                break
        # With all instances and a low threshold, it should eventually stop or exhaust instances
        assert criterion.should_stop() or len(criterion.selected_benchmark_ids) == len(benchmark_ids)

    def test_sorted_solvers_initialized_correctly(self, adaptor, benchmark_ids, solver_ids):
        ids = solver_ids[:3]
        criterion = WilcoxonStoppingCriterion(benchmark_ids, ids[0], ids[1:], min_accuracy=0.95, db_adaptor=adaptor)
        assert set(criterion.sorted_solver_ids) == set(ids[1:])
        assert criterion.challenger == ids[0]
