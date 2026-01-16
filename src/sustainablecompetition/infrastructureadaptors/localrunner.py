"""
Local Runner Adaptor
"""

import subprocess
from concurrent.futures import ProcessPoolExecutor
from sustainablecompetition.infrastructureadaptors.abstractrunner import AbstractRunner
from sustainablecompetition.benchmarkatoms import Job, Result
from sustainablecompetition.solveradaptors.abstractexecutable import AbstractExecutable
from sustainablecompetition.benchmarkadaptors.abstractinstance import AbstractInstanceAdaptor


def wrapper(solverpath: str, instancepath: str, job: Job):
    """Wrapper function to execute a job."""
    job.mark_running()
    result = subprocess.run([solverpath, instancepath], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
    return {"stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode}


class LocalRunner(AbstractRunner):
    """
    Initialize and maintain a process pool for local job execution.
    """

    def __init__(self, solver: AbstractExecutable, instances: AbstractInstanceAdaptor, parallel=1):
        super().__init__()
        self.solver = solver
        self.instances = instances
        self.pool = ProcessPoolExecutor(max_workers=parallel)
        self.futures = []

    def __del__(self):
        self.pool.shutdown(wait=True)

    def submit(self, job: Job):
        """
        Submit a function to the process pool.
        Return an id for identification of the process future.
        """
        solverpath = self.solver.get_path(job.solver_id)
        instancepath = self.instances.get_path(job.benchmark_id)
        future = self.pool.submit(wrapper, solverpath, instancepath, job)
        self.futures.append(future)
        super().submit(job)
        job.external_id = len(self.futures) - 1

    def completed(self, job: Job) -> Result:
        """
        Check if a job has completed.
        """
        extid = job.external_id
        future = self.futures[extid]
        if future.done():
            return Result(job, 0, 0)
        return None
