"""Stopping Criteria Interfaces."""

from abc import ABC, abstractmethod

from DIKEBenchmarker.benchmarkatoms import Result


__all__ = ["StoppingCriteria", "OrStoppingCriteria", "NoStoppingCriteria", "AndStoppingCriteria"]


class StoppingCriteria(ABC):
    """Decides when to stop submitting jobs."""
    
    def __init__(self):
        """Initialize the stopping criteria."""
        self.selected_benchmark_ids: list[str] = []

    @abstractmethod
    def should_stop(self) -> bool:
        """Return true if and only if the benchmarker has enough data to conclude."""
        raise NotImplementedError

    def handle_result(self, result: Result) -> None:
        """Called for each finished/failed job to update planning or process results."""
        pass
    
    def job_submitted(self, job) -> None:
        """Called for each submitted job to update planning or process results."""
        self.selected_benchmark_ids.append(job.benchmark_id)

    def __or__(self, value: "StoppingCriteria") -> "OrStoppingCriteria":
        """Create an OR combination of stopping criteria."""
        return OrStoppingCriteria([self, value])

    def __and__(self, value: "StoppingCriteria") -> "AndStoppingCriteria":
        """Create an AND combination of stopping criteria."""
        return AndStoppingCriteria([self, value])


class OrStoppingCriteria(StoppingCriteria):
    """Stops when any of the stopping criterion is true."""

    def __init__(self, criteria: list[StoppingCriteria]):
        """Initialize with a list of stopping criteria."""
        super().__init__()
        self.criteria: list[StoppingCriteria] = []
        for c in criteria:
            if isinstance(c, OrStoppingCriteria):
                self.criteria += c.criteria
            else:
                self.criteria.append(c)

    def should_stop(self) -> bool:
        """Return True if any criterion should stop."""
        return any(c.should_stop() for c in self.criteria)

    def handle_result(self, result: Result) -> None:
        """Handle result by passing it to all criteria."""
        for c in self.criteria:
            c.handle_result(result)
            
    def job_submitted(self, job) -> None:
        """Handle job submission by passing it to all criteria."""
        for c in self.criteria:
            c.job_submitted(job)


class NoStoppingCriteria(StoppingCriteria):
    """Never stops."""

    def should_stop(self) -> bool:
        """Return False always."""
        return False

    def handle_result(self, result: Result) -> None:
        """Handle result (no-op)."""
        pass

    def job_submitted(self, job) -> None:
        """Handle job submission (no-op)."""
        pass


class AndStoppingCriteria(StoppingCriteria):
    """Stops when all of the stopping criterion is true."""

    def __init__(self, criteria: list[StoppingCriteria]):
        """Initialize with a list of stopping criteria."""
        super().__init__()
        self.criteria: list[StoppingCriteria] = []
        for c in criteria:
            if isinstance(c, AndStoppingCriteria):
                self.criteria += c.criteria
            else:
                self.criteria.append(c)

    def should_stop(self) -> bool:
        """Return True if all criteria should stop."""
        return all(c.should_stop() for c in self.criteria)

    def handle_result(self, result: Result) -> None:
        """Handle result by passing it to all criteria."""
        for c in self.criteria:
            c.handle_result(result)

    def job_submitted(self, job) -> None:
        """Handle job submission by passing it to all criteria."""
        for c in self.criteria:
            c.job_submitted(job)
