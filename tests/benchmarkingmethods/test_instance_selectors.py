from importlib.resources import files
import pytest


from sustainablecompetition.benchmarkatoms import Job
from sustainablecompetition.benchmarkingmethods.instance_selectors.discrimination_instance_selector import DiscriminationInstanceSelector
from sustainablecompetition.benchmarkingmethods.instance_selectors.random_instance_selector import RandomInstanceSelector
from sustainablecompetition.benchmarkingmethods.instance_selectors.variance_instance_selector import VarianceInstanceSelector
from sustainablecompetition.dataadaptors.sqlite_dataadaptor import SqlDataAdaptor


def build_adaptor() -> SqlDataAdaptor:
    db_path = files("sustainablecompetition.data.db").joinpath("sustainablecompetition.db")
    db_adaptor = SqlDataAdaptor(db_path)
    return db_adaptor


INSTANCE_SELECTORS = [
    lambda bench_ids, solver_id, adap: VarianceInstanceSelector(bench_ids, solver_id, adap),
    lambda bench_ids, solver_id, adap: RandomInstanceSelector(bench_ids, solver_id),
    lambda bench_ids, solver_id, adap: DiscriminationInstanceSelector(bench_ids, solver_id, adap),
]
INSTANCE_SELECTOR_NAMES = ["VarianceInstanceSelector", "RandomInstanceSelector", "DiscriminationInstanceSelector"]


@pytest.mark.parametrize("instance_selector_builder", INSTANCE_SELECTORS, ids=INSTANCE_SELECTOR_NAMES)
def test_run_all_jobs(instance_selector_builder):
    adaptor = build_adaptor()
    benchmark_ids = list(set(adaptor.get_performances().get_column("inst_hash").to_list()))
    jobs_left = len(benchmark_ids)
    solver_id = adaptor.get_competition_solver_id("main2024")
    selector = instance_selector_builder(benchmark_ids, solver_id, adaptor)
    benchs_done = set()
    while jobs_left > 0:
        bench: Job = selector.next_benchmark_id()
        assert bench is not None, f"returned a job with a None benchmark hash while there are still {jobs_left} jobs left"
        assert bench not in benchs_done, "produced the same job twice"
        benchs_done.add(bench)
        jobs_left -= 1


@pytest.mark.parametrize("instance_selector_builder", INSTANCE_SELECTORS, ids=INSTANCE_SELECTOR_NAMES)
def test_valid_jobs(instance_selector_builder):
    adaptor = build_adaptor()
    benchmark_ids = list(set(adaptor.get_performances().get_column("inst_hash").to_list()))
    jobs_left = len(benchmark_ids)
    solver_id = adaptor.get_competition_solver_id("main2024")
    selector = instance_selector_builder(benchmark_ids, solver_id, adaptor)
    while jobs_left > 0:
        bench = selector.next_benchmark_id()
        assert bench in benchmark_ids, f'produced a job with invalid benchmark_id: "{bench}"'
        jobs_left -= 1
