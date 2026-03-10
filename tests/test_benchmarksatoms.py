import pytest
from datetime import datetime
from DikeBenchmarker.benchmarkatoms import Job, JobState, JobStateError

# ---- test job.mark_submitted() ----


def test_mark_submitted_success():
    # Setup
    job = Job(None, "bench_id", "solver_id", "checker_id", "./logs")
    job.state = JobState.CREATED

    # Action
    job.mark_submitted()

    # Assert
    assert job.state == JobState.SUBMITTED
    assert job.submitted_at is not None
    assert isinstance(job.submitted_at, datetime)


def test_mark_submitted_fails_if_not_created():
    # Setup
    job = Job(None, "bench_id", "solver_id", "checker_id", "./logs")
    job.state = JobState.RUNNING

    # Action & Assert
    with pytest.raises(JobStateError):
        job.mark_submitted()


# ---- Test job.mark_running() ----
def test_mark_running_success():
    # Setup
    job = Job(None, "bench_id", "solver_id", "checker_id", "./logs")
    job.state = JobState.SUBMITTED

    # Action
    job.mark_running()

    # Assert
    assert job.state == JobState.RUNNING
    assert job.started_at is not None
    assert isinstance(job.started_at, datetime)


def test_mark_running_fails_if_not_submitted():
    # Setup
    job = Job(None, "bench_id", "solver_id", "checker_id", "./logs")
    job.state = JobState.CREATED

    # Action & Assert
    with pytest.raises(JobStateError):
        job.mark_running()


# ---- test job.set_finished() ----
def test_set_finished_success():
    # Setup
    job = Job(None, "bench_id", "solver_id", "checker_id", "./logs")
    job.state = JobState.RUNNING

    # Action
    job.set_finished()

    # Assert
    assert job.state == JobState.FINISHED
    assert job.finished_at is not None
    assert isinstance(job.finished_at, datetime)


def test_set_finished_fails_if_not_running():
    # Setup
    job = Job(None, "bench_id", "solver_id", "checker_id", "./logs")
    job.state = JobState.SUBMITTED

    # Action & Assert
    with pytest.raises(JobStateError):
        job.set_finished()


# ---- test job.set_failed(error_msg) ----
def test_set_failed_success():
    # Setup
    job = Job(None, "bench_id", "solver_id", "checker_id", "./logs")
    job.state = JobState.RUNNING
    error_msg = "Test error message"

    # Action
    job.set_failed(error_msg)

    # Assert
    assert job.state == JobState.FAILED
    assert job.error == error_msg
    assert job.finished_at is not None
    assert isinstance(job.finished_at, datetime)


def test_set_failed_fails_if_not_running():
    # Setup
    job = Job(None, "bench_id", "solver_id", "checker_id", "./logs")
    job.state = JobState.SUBMITTED
    error_msg = "Test error message"

    # Action & Assert
    with pytest.raises(JobStateError):
        job.set_failed(error_msg)


# ---- test job.cancel_local() ----
def test_cancel_local_success_for_created():
    # Setup
    job = Job(None, "bench_id", "solver_id", "checker_id", "./logs")
    job.state = JobState.CREATED

    # Action
    result = job.cancel_local()

    # Assert
    assert result is True
    assert job.state == JobState.CANCELLED
    assert job.finished_at is not None
    assert isinstance(job.finished_at, datetime)


def test_cancel_local_success_for_submitted():
    # Setup
    job = Job(None, "bench_id", "solver_id", "checker_id", "./logs")
    job.state = JobState.SUBMITTED

    # Action
    result = job.cancel_local()

    # Assert
    assert result is True
    assert job.state == JobState.CANCELLED
    assert job.finished_at is not None
    assert isinstance(job.finished_at, datetime)


def test_cancel_local_fails_for_running():
    # Setup
    job = Job(None, "bench_id", "solver_id", "checker_id", "./logs")
    job.state = JobState.RUNNING

    # Action
    result = job.cancel_local()

    # Assert
    assert result is False
    assert job.state == JobState.RUNNING
    assert job.finished_at is None
