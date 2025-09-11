import importlib
import pytest


from sustainablecompetition.benchmarkatoms import Job
from sustainablecompetition.benchmarkingmethods.instance_selectors.random_instance_selector import RandomInstanceSelector
from sustainablecompetition.benchmarkingmethods.instance_selectors.variance_instance_selector import VarianceInstanceSelector
from sustainablecompetition.dataadaptors.sqlite_dataadaptor import SqlDataAdaptor


def build_adaptor() -> SqlDataAdaptor:
    db_path = importlib.resources.files("sustainablecompetition.data").joinpath("sustainablecompetition.db")
    db_adaptor = SqlDataAdaptor(db_path)
    return db_adaptor


INSTANCE_SELECTORS = [
    lambda bench_ids, solver_id, adap: VarianceInstanceSelector(bench_ids, solver_id, adap),
    lambda bench_ids, solver_id, adap: RandomInstanceSelector(bench_ids, solver_id),
]
INSTANCE_SELECTOR_NAMES = ["VarianceInstanceSelector", "RandomInstanceSelector"]


@pytest.mark.parametrize("instance_selector_builder", INSTANCE_SELECTORS, ids=INSTANCE_SELECTOR_NAMES)
def test_run_all_jobs(instance_selector_builder):
    adaptor = build_adaptor()
    benchmark_ids = adaptor.get_performances().get_column("inst_hash").to_list()
    jobs_left = len(benchmark_ids)
    solver_id = adaptor.get_competition_solver_hash("main2024")
    selector = instance_selector_builder(benchmark_ids, solver_id, adaptor)
    jobs_done = set()
    while jobs_left > 0:
        job: Job = selector.next_job()
        assert job is not None, f"returned no job while there are still {jobs_left} jobs left"
        assert job.benchmark_id is not None, f"returned a job with a None benchmark hash while there are still {jobs_left} jobs left"
        assert job.benchmark_id not in jobs_done, "produced the same job twice"
        jobs_done.add(job.benchmark_id)
        jobs_left -= 1


@pytest.mark.parametrize("instance_selector_builder", INSTANCE_SELECTORS, ids=INSTANCE_SELECTOR_NAMES)
def test_valid_jobs(instance_selector_builder):
    adaptor = build_adaptor()
    benchmark_ids = adaptor.get_performances().get_column("inst_hash").to_list()
    jobs_left = len(benchmark_ids)
    solver_id = adaptor.get_competition_solver_hash("main2024")
    selector = instance_selector_builder(benchmark_ids, solver_id, adaptor)
    while jobs_left > 0:
        job: Job = selector.next_job()
        assert job is not None
        assert job.benchmark_id in benchmark_ids, f'produced a job with invalid benchmark_id: "{job.benchmark_id}"'
        assert job.solver_id == solver_id, f'produced a job with invalid solver_id: "{job.solver_id}"'
        jobs_left -= 1
