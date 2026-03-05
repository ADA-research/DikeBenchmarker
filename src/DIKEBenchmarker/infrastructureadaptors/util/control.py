"""Control module for graceful shutdown and SLURM job requeuing."""
import signal
import os
import subprocess

import parsl


_SLURM_REQUEUE_SCRIPT_PATH = None
_SHUTTING_DOWN = False


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

    if has_slurm_requeue_script_path():
        submit_slurm_requeue_job()
        unset_slurm_requeue_script_path()  # avoid multiple submissions if multiple signals are received

    parsl.dfk().cleanup()
    parsl.clear()


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
    res = subprocess.run(["sbatch", _SLURM_REQUEUE_SCRIPT_PATH], capture_output=True, text=True, check=False)
    print("OUT:", res.stdout, "ERR:", res.stderr, "RETURN CODE:", res.returncode)
