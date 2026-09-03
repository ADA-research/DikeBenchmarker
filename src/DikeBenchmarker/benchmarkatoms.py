"""Basic benchmarking job and result representation"""

import logging
import itertools
from dataclasses import dataclass, fields, is_dataclass
from enum import Enum
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from DikeBenchmarker.benchmarkingmethods.benchmarker import AbstractBenchmarker

logger = logging.getLogger(__name__)


class JobState(Enum):
    """Possible states of a Job."""

    CREATED = 1
    SUBMITTED = 2
    RUNNING = 3
    FINISHED = 4
    FAILED = 5
    CANCELLED = 6


class JobStateError(Exception):
    """Raised when an invalid state transition is attempted on a Job."""


class Job:
    """Benchmarking Job that behaves like a future.

    Identity: benchmark_id, solver_id, created_at (ctor time).

    Lifecycle:

      CREATED (initial)
        --[put into JobLog]--> SUBMITTED
        --[start working on]--> RUNNING
        --[finish working on]--> FINISHED | FAILED

      CREATED/SUBMITTED -> CANCELLED
    """

    _id_counter = itertools.count()

    def __init__(
        self,
        job_producer: "AbstractBenchmarker",
        benchmark_id: str,
        solver_id: str,
        checker_id: str,
        logroot: str,
        retries: int = 3,
    ) -> None:
        self.uid = next(Job._id_counter)

        self.job_producer: "AbstractBenchmarker" = job_producer
        self.benchmark_id: str = benchmark_id
        self.solver_id: str = solver_id
        self.checker_id: str = checker_id
        self.logroot: str = logroot

        # timestamps
        self.created_at: datetime = datetime.now(timezone.utc)
        self.submitted_at: Optional[datetime] = None
        self.started_at: Optional[datetime] = None
        self.finished_at: Optional[datetime] = None

        # state data
        self.state: JobState = JobState.CREATED
        self.result: Optional["Result"] = None

    def clone_retry(self, decrement: int = 1) -> "Job":
        """Create a clone of this job with identical benchmark_id, solver_id, checker_id, and logroot.
        
        The cloned job will have a new created_at timestamp and will be in the CREATED state.
        """
        return Job(
            job_producer=self.job_producer,
            benchmark_id=self.benchmark_id,
            solver_id=self.solver_id,
            checker_id=self.checker_id,
            logroot=self.logroot,
        )

    def get_log_prefix(self) -> str:
        """Get the logfile prefix for this job."""
        return f"{self.logroot}/{self.solver_id}/{self.solver_id}.{self.benchmark_id}"

    def mark_submitted(self) -> None:
        """Mark the job as submitted.
        
        Called by the infrastructure adaptor upon receiving the job.
        """
        if self.state == JobState.SUBMITTED:
            logger.warning(f"job {self} wants to be marked as {self.state.name} but it already is {self.state.name}")
            if self.submitted_at is None:
                self.submitted_at = datetime.now(timezone.utc)
            return
        if self.state != JobState.CREATED:
            raise JobStateError(f"Cannot mark job as SUBMITTED from state {self.state.name}")
        self.state = JobState.SUBMITTED
        self.submitted_at = datetime.now(timezone.utc)

    def mark_running(self) -> None:
        """Mark the job as running.
        
        Called by the infrastructure adaptor once the job started to run.
        """
        if self.state == JobState.RUNNING:
            logger.warning(f"job {self} wants to be marked as {self.state.name} but it already is {self.state.name}")
            return
        if self.state != JobState.SUBMITTED:
            raise JobStateError(f"Cannot mark job as RUNNING from state {self.state.name}")
        self.state = JobState.RUNNING
        self.started_at = datetime.now(timezone.utc)

    def set_finished(self) -> None:
        """Mark the job as finished.
        
        Called by the infrastructure adaptor when the job has completed successfully.
        """
        if self.state != JobState.RUNNING:
            raise JobStateError(f"Cannot mark job as FINISHED from state {self.state.name}")
        self.state = JobState.FINISHED
        self.finished_at = datetime.now(timezone.utc)

    def set_failed(self) -> None:
        """Mark the job as failed.
        
        Called by the infrastructure adaptor when the job has completed unsuccessfully.
        """
        if self.state != JobState.RUNNING:
            raise JobStateError(f"Cannot mark job as FAILED from state {self.state.name}")
        self.state = JobState.FAILED
        self.finished_at = datetime.now(timezone.utc)

    def cancel_local(self) -> bool:
        """Mark the job as cancelled.
        
        Called by the benchmarker to prevent the job from being submitted to the external system.
        """
        if self.state in (JobState.CREATED, JobState.SUBMITTED):
            self.state = JobState.CANCELLED
            self.finished_at = datetime.now(timezone.utc)
            return True
        return False

    def __repr__(self) -> str:
        return f"Job({self.benchmark_id!r}, {self.solver_id!r}, {self.state.name})"


@dataclass
class AbstractResult:
    """Mixin providing baseline functionality for result atoms."""

    state: Enum
    detail: Optional[str] = None

    def __init_subclass__(cls, **kw):
        """Ensure that subclasses define the required base state members."""
        super().__init_subclass__(**kw)
        names = {m.name for m in cls.State}
        missing = {"NONE", "ERROR"} - names
        if missing:
            raise TypeError(f"{cls.__name__}.State missing required member(s): {missing}")

    @property
    def is_empty(self) -> bool:
        """Return True if the result atom has no data (state is NONE)."""
        return self.state.name == "NONE"

    @property
    def has_error(self) -> bool:
        """Return True if the result atom encountered an error (state is ERROR)."""
        return self.state.name == "ERROR"

    @property
    def has_result(self) -> bool:
        """Return True if the result atom has a valid, non-error result."""
        return not self.is_empty and not self.has_error
    
    @property
    def has_detail(self) -> bool:
        """Return True if the result atom has a detail message."""
        return self.detail is not None
    
    @property
    def get_detail(self) -> Optional[str]:
        """Return the detail message of the result atom."""
        return self.detail
    
    
@dataclass
class ExecutionResult(AbstractResult):
    """Execution outcome of one wrapped job."""
    
    class State(str, Enum):
        """Possible execution verdicts a wrapper can report."""

        NONE = "none"
        ERROR = "error"
        SUCCESS = "success"

    state: "ExecutionResult.State" = State.NONE


@dataclass
class ResourceResult(AbstractResult):
    """Resource usage and limit outcome of one wrapped execution."""

    class State(str, Enum):
        """Possible resource-limit verdicts a wrapper can report."""
    
        NONE = "none"
        ERROR = "error"
        SUCCESS = "success"
        TIMEOUT = "timeout"
        MEMOUT = "memout"

    state: "ResourceResult.State" = State.NONE
    cputime: Optional[float] = None  # seconds
    walltime: Optional[float] = None  # seconds
    memory: Optional[float] = None  # MiB


@dataclass
class SolverResult(AbstractResult):
    """Satisfiability verdict reported by a solver."""

    class State(str, Enum):
        """Possible satisfiability verdicts a solver can report."""

        NONE = "none"
        ERROR = "error"
        SAT = "sat"
        UNSAT = "unsat"
        UNKNOWN = "unknown"

    state: "SolverResult.State" = State.NONE


@dataclass
class CheckerResult(AbstractResult):
    """Verdict reported by a proof/model checker."""

    class State(str, Enum):
        """Possible verdicts a checker can report."""

        NONE = "none"
        ERROR = "error"
        VERIFIED = "verified"
        UNVERIFIED = "unverified"
        UNKNOWN = "unknown"

    state: "CheckerResult.State" = State.NONE


class Result:
    """Aggregate benchmarking result composed of independent per-dimension atoms."""

    def __init__(self, job: "Job"):
        """Initialize the Result with a job and optional result atoms."""
        self.job = job
        self.execution = ExecutionResult()
        self.solver = SolverResult()
        self.checker = CheckerResult()
        self.solver_resources = ResourceResult()
        self.checker_resources = ResourceResult()

    def get_job(self) -> "Job":
        """Return the job object associated with this result."""
        return self.job

    def _atoms(self) -> list[AbstractResult]:
        """Return every attached result atom."""
        return [v for v in vars(self).values() if is_dataclass(v)]

    @property
    def is_empty(self) -> bool:
        """Return True only if every atom is still empty (nothing has produced data yet)."""
        return all(atom.is_empty for atom in self._atoms())

    @property
    def has_error(self) -> bool:
        """Return True if any atom reports an error."""
        return any(atom.has_error for atom in self._atoms())

    @property
    def has_result(self) -> bool:
        """Return True if any atom produced a valid, non-error result."""
        return any(atom.has_result for atom in self._atoms())

    @property
    def detail(self) -> Optional[str]:
        """Join every atom's detail message, namespaced by atom name."""
        parts = [f"{name}: {atom.detail}" for name, atom in vars(self).items() if is_dataclass(atom) and atom.has_detail]
        return "; ".join(parts) if parts else None

    def to_eval_record(self) -> dict:
        """Flatten every attached atom's fields into a namespaced dict."""
        rec = {"inst_id": self.job.benchmark_id, "solver_id": self.job.solver_id, "checker_id": self.job.checker_id}
        for name, atom in vars(self).items():
            if is_dataclass(atom):
                for f in fields(atom):
                    v = getattr(atom, f.name)
                    rec[f"{name}.{f.name}"] = v.value if isinstance(v, Enum) else v
        return rec

    def __repr__(self):
        """Return a string representation of the Result."""
        atoms = ", ".join(f"{k}={v!r}" for k, v in vars(self).items() if k != "job" and is_dataclass(v))
        return f"Result(inst_id={self.job.benchmark_id!r}, solver_id={self.job.solver_id!r}, {atoms})"
