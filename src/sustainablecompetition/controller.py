from sustainablecompetition.benchmarkatoms import Result
from sustainablecompetition.benchmarkingmethods.benchmarkerinterface import Benchmarker
from sustainablecompetition.infrastructureadapters.abstractrunner import AbstractRunner
from sustainablecompetition.resultconsumers.resultconsumer import ResultConsumer


class Controller:
    """
    Connects the benchmarking method with the infrastructure adapter.
    """

    def __init__(self, benchmarker: Benchmarker, runner: AbstractRunner, njobs: int = 1, consumers: list[ResultConsumer] = []):
        self.benchmarker = benchmarker
        self.runner = runner
        self.njobs = njobs
        self.consumers = consumers

    def run(self):
        """
        Maintains the benchmarking process and blocks until benchmarking is finished (i.e., all jobs are completed).
        """
        # submit njobs to the runner
        for _ in range(self.njobs):
            job = self.benchmarker.next_job()
            if job is not None:
                self.runner.submit(job)
        # iterate over the results
        for result in self.runner.completions():
            self.benchmarker.handle_result(result)
            # submit the next job
            job = self.benchmarker.next_job()
            if job is not None:
                self.runner.submit(job)
            self.__process_result__(result)

    def __process_result__(self, result: Result):
        for consumer in self.consumers:
            consumer.consume_result(result)
