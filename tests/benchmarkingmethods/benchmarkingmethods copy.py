import importlib
import pytest
import polars as pl


from sustainablecompetition.benchmarkatoms import Job
from sustainablecompetition.benchmarkingmethods.trivial_benchmarker import TrivialBenchmarker
from sustainablecompetition.benchmarkingmethods.instance_selectors.variance_instance_selector import VarianceInstanceSelector
from sustainablecompetition.dataadaptors.competition_dataadaptor import CompetitionDataAdaptor
from sustainablecompetition.dataadaptors.dataadaptor import DataAdaptor


def build_adaptor() -> DataAdaptor:
    db_path = importlib.resources.files("sustainablecompetition.data").joinpath("sustainablecompetition.db")

    cp_adaptor = CompetitionDataAdaptor.from_competition_csv("./examples/dataAdaptors/sat/main2024.csv", source_name="main2024", database_path=db_path)
    return cp_adaptor


INSTANCE_SELECTORS = [lambda bench_ids, solver_id, adap: VarianceInstanceSelector(bench_ids, solver_id, adap)]
INSTANCE_SELECTOR_NAMES = ["VarianceInstanceSelector"]


@pytest.mark.parametrize("benchmarker_builder", INSTANCE_SELECTORS, ids=INSTANCE_SELECTOR_NAMES)
def test_run_all_jobs(instance_builder):
    adaptor = build_adaptor()
    jobs_done = set()
    while jobs_left > 0:
        job: Job = benchmarker.next_job()
        assert job is not None, f"returned no job while there are still {jobs_left} jobs left"
        assert job.benchmark_id not in jobs_done, "produced the same job twice"
        jobs_done.add(job.benchmark_id)
        jobs_left -= 1


BENCHMARKERS = [
    lambda bench_ids, solver_id, adap: TrivialBenchmarker(bench_ids, solver_id),
]
BENCHMARKERS_NAMES = ["TrivialBenchmarker"]


@pytest.mark.parametrize("benchmarker_builder", builders, ids=TEST_IDS)
def test_run_all_jobs(benchmarker_builder):
    jobs_left = NJOBS
    benchmarker = benchmarker_builder()
    jobs_done = set()
    while jobs_left > 0:
        job: Job = benchmarker.next_job()
        assert job is not None, f"returned no job while there are still {jobs_left} jobs left"
        assert job.benchmark_id not in jobs_done, "produced the same job twice"
        jobs_done.add(job.benchmark_id)
        jobs_left -= 1


@pytest.mark.parametrize("benchmarker_builder", builders, ids=TEST_IDS)
def test_valid_jobs(benchmarker_builder):
    jobs_left = NJOBS
    benchmarker = benchmarker_builder()
    while jobs_left > 0:
        job: Job = benchmarker.next_job()
        assert job is not None
        assert job.benchmark_id in BENCHMARK_IDS, f'produced a job with invalid benchmark_id: "{job.benchmark_id}"'
        assert job.solver_id == SOLVER_ID, f'produced a job with invalid solver_id: "{job.solver_id}"'
        jobs_left -= 1
