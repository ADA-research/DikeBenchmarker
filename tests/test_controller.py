import polars as pl
from DikeBenchmarker.benchmarkatoms import Result
from DikeBenchmarker.benchmarkingmethods.benchmarker import TrivialBenchmarker
from DikeBenchmarker.dataadaptors.competition_dataadaptor import CompetitionDataAdaptor
from DikeBenchmarker.infrastructureadaptors.virtual_runner import VirtualRunner
from DikeBenchmarker.resultconsumers.lambda_consumer import LambdaConsumer


def test_run():
    NJOBS = 50
    BENCHMARK_IDS = [str(i) for i in range(NJOBS)]
    NSOLVERS = 10
    df = pl.DataFrame({"hash": BENCHMARK_IDS, **{str(solver_id): [int(solver_id)] * NJOBS for solver_id in range(NSOLVERS)}})
    runner = VirtualRunner(CompetitionDataAdaptor(df))
    benchmarks = df.select("hash").to_series().to_list()
    columns = df.columns
    method = TrivialBenchmarker(benchmarks, columns[1])
    results: list[Result] = []
    consumer = LambdaConsumer(results.append)
    method.register_consumer(consumer)
    runner.run([method], NJOBS)

    assert len(results) == NJOBS
