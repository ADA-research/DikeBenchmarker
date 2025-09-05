import pytest
import polars as pl


from sustainablecompetition.benchmarkatoms import Job
from sustainablecompetition.benchmarkingmethods.trivial_benchmarker import TrivialBenchmarker
from sustainablecompetition.benchmarkingmethods.variance_benchmarker import VarianceBenchmarker
from sustainablecompetition.dataadapters.competition_dataadapter import CompetitionDataAdapter


NJOBS = 50
BENCHMARK_IDS = [str(i) for i in range(NJOBS)]
SOLVER_ID = "1"
NSOLVERS = 10
NPOINTS = 10


builders = [
    lambda: TrivialBenchmarker(BENCHMARK_IDS, SOLVER_ID),
    lambda: VarianceBenchmarker(
        BENCHMARK_IDS,
        SOLVER_ID,
        CompetitionDataAdapter(
            pl.DataFrame(
                {
                    "hash": BENCHMARK_IDS * NPOINTS,
                    "solver_id": [str(i) for i in range(NSOLVERS)] * (NPOINTS * NJOBS // NSOLVERS),
                    "runtime": [int(i) for i in range(NPOINTS * NJOBS)],
                }
            )
        ),
    ),
]

TEST_IDS = [
    "TrivialBenchmarker",
    "VarianceBenchmarker"
]


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
