import asyncio
from sustainablecompetition.benchmarkingmethods.benchmarkerinterface import Benchmarker
from sustainablecompetition.infrastructureadapters.abstractrunner import AbstractRunner
from sustainablecompetition.resultconsumers.resultconsumer import ResultConsumer


__all__ = ["Controller"]


class Controller:
    """
    Connects the benchmarking method with the infrastructure adapter.
    """

    def __init__(self, benchmarker: Benchmarker, runner: AbstractRunner, njobs: int = 1, consumers: list[ResultConsumer] = None):
        self.benchmarker = benchmarker
        self.runner = runner
        self.njobs = njobs
        self.consumers = consumers if consumers is not None else []

    async def run(self):
        """
        Maintains the benchmarking process and blocks until benchmarking is finished (i.e., all jobs are completed).
        Also blocks until all consumers are finished.
        """
        tasks = set()
        # submit njobs to the runner
        for _ in range(self.njobs):
            job = self.benchmarker.next_job()
            if job is not None:
                self.runner.submit(job)
        # iterate over the results
        async for result in self.runner.completions():
            self.benchmarker.handle_result(result)
            # submit the next job
            job = self.benchmarker.next_job()
            if job is not None:
                self.runner.submit(job)
            for consumer in self.consumers:
                task = asyncio.create_task(consumer.consume_result(result))
                tasks.add(task)

                task.add_done_callback(tasks.discard)

        if tasks:
            await asyncio.gather(*tasks)
