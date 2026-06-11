"""Control module for graceful shutdown and SLURM job requeuing."""

import signal
import os
import subprocess

import parsl


_SLURM_REQUEUE_SCRIPT_PATH = None
_SHUTTING_DOWN = False
_ALL_JOBS_COMPLETE = False


def flag_all_jobs_complete():
    """Flag that all jobs have finished, so no requeue is needed on shutdown."""
    global _ALL_JOBS_COMPLETE
    _ALL_JOBS_COMPLETE = True


def all_jobs_complete() -> bool:
    """Check whether all jobs have already finished."""
    return _ALL_JOBS_COMPLETE


def flag_shutting_down():
    """Flag that the system is shutting down."""
    global _SHUTTING_DOWN
    _SHUTTING_DOWN = True


def is_shutting_down() -> bool:
    """Check if the system is shutting down."""
    return _SHUTTING_DOWN


def shutdown(signum, frame):
    """Signal handler for graceful shutdown when walltime is approaching."""
    print(f"Received signal {signum}, initiating graceful shutdown...")

    if is_shutting_down():
        return
    flag_shutting_down()

    # Only requeue if there is still pending work; a run that already finished
    # all its jobs must not spawn a continuation just because SLURM sent the
    # pre-walltime signal to the still-alive controller process.
    if has_slurm_requeue_script_path() and not all_jobs_complete():
        submit_slurm_requeue_job()
        unset_slurm_requeue_script_path()  # avoid multiple submissions if multiple signals are received

    cleanup_parsl()


def cleanup_parsl():
    """Tear down the parsl DFK, scancel'ing any worker blocks.

    Idempotent: safe to call more than once and whether or not parsl is
    currently loaded (if it is not, parsl.dfk() raises and is ignored).
    """
    try:
        parsl.dfk().cleanup()
        parsl.clear()
    except Exception as e:
        print(f"parsl cleanup skipped or already done: {e}")


def register_shutdown_handler():
    """Register signal handlers for graceful shutdown.

    - SIGINT: Keyboard interrupt (Ctrl+C)
    - SIGTERM: Termination request (e.g., kill command)
    - SIGHUP: Terminal closed or parent process terminated
    - SIGUSR1: User-defined signal 1 (custom timeout notification)

    In SLURM jobs, use `#SBATCH --signal=B:USR1@300` to send SIGUSR1
    300 seconds before walltime limit, allowing graceful shutdown before timeout.
    """
    print("Registering signal handlers for graceful shutdown...")
    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP, signal.SIGUSR1):
        signal.signal(sig, shutdown)


def set_slurm_requeue_script_path(path: str):
    """Set the path to the SLURM script for requeuing."""
    global _SLURM_REQUEUE_SCRIPT_PATH
    if not os.path.exists(path):
        print(f"Error: SLURM requeue script {path} does not exist.")
        return
    if not os.access(path, os.R_OK):
        print(f"Error: SLURM requeue script {path} is not readable.")
        return
    _SLURM_REQUEUE_SCRIPT_PATH = path


def unset_slurm_requeue_script_path():
    """Unset the path to the SLURM script for requeuing."""
    global _SLURM_REQUEUE_SCRIPT_PATH
    _SLURM_REQUEUE_SCRIPT_PATH = None


def has_slurm_requeue_script_path() -> bool:
    """Check if the SLURM requeue script path is set."""
    return _SLURM_REQUEUE_SCRIPT_PATH is not None


def submit_slurm_requeue_job():
    """Submit a SLURM job for the next batch using the registered script path."""
    print(f"Submitting SLURM job for next batch using script at {_SLURM_REQUEUE_SCRIPT_PATH}...")
    cmd = ["sbatch"]
    # Preserve the original job name (set by submit.sh) so the continuation
    # appears under the same name in the queue instead of the script default.
    job_name = os.environ.get("SLURM_JOB_NAME")
    if job_name:
        cmd += ["--job-name", job_name]
    cmd.append(_SLURM_REQUEUE_SCRIPT_PATH)
    res = subprocess.run(cmd, capture_output=True, text=True, check=False)
    print("OUT:", res.stdout, "ERR:", res.stderr, "RETURN CODE:", res.returncode)
