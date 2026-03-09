"""Local Runner Adaptor."""

import subprocess
from concurrent.futures import ProcessPoolExecutor
from DIKEBenchmarker.infrastructureadaptors.abstract_runner import AbstractRunner
from DIKEBenchmarker.benchmarkatoms import Job, Result
from DIKEBenchmarker.solveradaptors.abstractexecutable import AbstractExecutable
from DIKEBenchmarker.benchmarkadaptors.abstractinstance import AbstractInstanceAdaptor


def wrapper(solverpath: str, instancepath: str, job: Job):
    """Wrapper function to execute a job."""
    job.mark_running()
    result = subprocess.run([solverpath, instancepath], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
    return {"stdout": result.stdout, "stderr": result.stderr, "returncode": result.returncode}


class LocalRunner(AbstractRunner):
    """Initialize and maintain a process pool for local job execution."""

    def __init__(self, solver: AbstractExecutable, instances: AbstractInstanceAdaptor, parallel=1):
        """Initialize the local runner with solver, instances, and parallelism level."""
        super().__init__()
        self.solver = solver
        self.instances = instances
        self.pool = ProcessPoolExecutor(max_workers=parallel)
        self.futures_map = {}  # maps job uid to future for easy lookup in completed()

    def __del__(self):
        """Clean up the process pool when the runner is destroyed."""
        self.pool.shutdown(wait=True)

    def submit(self, job: Job):
        """Submit a function to the process pool.

        Return an id for identification of the process future.
        """
        if not super().submit(job):
            return False

        job.mark_running()

        solverpath = self.solver.get_path(job.solver_id)
        instancepath = self.instances.get_path(job.benchmark_id)
        future = self.pool.submit(wrapper, solverpath, instancepath, job)

        self.futures_map[job.uid] = future

        return True

    def completed(self, job: Job) -> Result:
        """Check if a job has completed."""
        future = self.futures_map[job.uid]
        if future.done():
            return Result(job, 0, 0)
        return None
