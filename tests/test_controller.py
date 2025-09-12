import polars as pl
from sustainablecompetition.benchmarkatoms import Result
from sustainablecompetition.benchmarkingmethods.trivial_benchmarker import TrivialBenchmarker
from sustainablecompetition.controller import Controller
from sustainablecompetition.dataadaptors.competition_dataadaptor import CompetitionDataAdaptor
from sustainablecompetition.infrastructureadaptors.virtual_runner import VirtualRunner
from sustainablecompetition.resultconsumers.lambda_consumer import LambdaConsumer


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
    controller = Controller(method, runner, njobs=1, consumers=[consumer])
    controller.run()
    assert len(results) == NJOBS
