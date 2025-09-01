from typing import AsyncIterator
from abc import ABC, abstractmethod

from BenchmarkAtoms import Job, Result


class Benchmarker(ABC):
    """Decides which jobs to submit next; can depend on past results/dependencies."""

    @abstractmethod
    async def next_job(self) -> Job:
        """Return the next job to submit (can be None if no job is ready)."""
        raise NotImplementedError

    @abstractmethod
    async def handle_result(self, result: Result) -> None:
        """Called for each finished/failed job to update planning or process results."""
        raise NotImplementedError


class Infrastructure(ABC):
    """
    Adapter to execution environment (cluster, SLURM, K8s, cloud API, vendor queue).
    """

    @abstractmethod
    async def submit(self, job: Job):
        """Submit a job to the external system."""
        raise NotImplementedError

    @abstractmethod
    async def completions(self) -> AsyncIterator[Result]:
        """
        Async stream of results.
        Must yield whenever the external system reports a job as done/failed.
        """
        raise NotImplementedError

    @abstractmethod
    async def cancel(self, external_id: str) -> bool:
        """Best-effort cancellation if supported by the external system."""
        return False
