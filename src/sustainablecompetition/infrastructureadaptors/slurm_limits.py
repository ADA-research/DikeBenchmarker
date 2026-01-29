"""
This module provides functions to interact with Slurm workload manager
to retrieve user job limits, current job counts, and quality of service (QOS) information.

Functions:
- get_current_jobs: Returns the number of current jobs for a specified user.
- get_user_limits: Retrieves the maximum job limits for a specified user.
- get_user_qos: Gets the quality of service (QOS) associated with a user.
- get_qos_limits: Retrieves the maximum job limits for a specified QOS.
- compute_max_blocks: Computes the maximum number of blocks a user can run based on limits and current jobs.
"""

import subprocess
import getpass
import re
from typing import Optional


def _run(cmd: str) -> str:
    """Run shell command and return stdout or empty string."""
    try:
        return subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return ""


def _parse_int(value: str) -> Optional[int]:
    """
    Parse Slurm integer fields.
    Returns None if unlimited or missing.
    """
    if not value:
        return None
    value = value.strip()
    if value.upper() in {"UNLIMITED", "INFINITE", "N/A"}:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def get_current_jobs(user: str) -> int:
    """
    Returns the number of currently running jobs for the specified user.
    """
    out = _run(f"squeue -u {user} -h | wc -l")
    try:
        return int(out)
    except Exception:
        return 0


def get_user_limits(user: str):
    """
    Returns (MaxJobs, MaxSubmitJobs)
    """
    out = _run(f"sacctmgr show user {user} withassoc format=MaxJobs,MaxSubmitJobs -n")

    max_jobs = None
    max_submit = None

    for line in out.splitlines():
        parts = re.split(r"\s+", line.strip())
        if len(parts) >= 2:
            max_jobs = _parse_int(parts[0]) or max_jobs
            max_submit = _parse_int(parts[1]) or max_submit

    return max_jobs, max_submit


def get_user_qos(user: str) -> Optional[str]:
    """
    Returns the QOS of the specified user.
    """
    out = _run(f"sacctmgr show assoc where user={user} format=QOS -n")
    for line in out.splitlines():
        qos = line.strip()
        if qos:
            return qos
    return None


def get_qos_limits(qos: str):
    """
    Returns (MaxJobs, MaxSubmitJobs)
    """
    out = _run(f"sacctmgr show qos {qos} format=MaxJobs,MaxSubmitJobs -n")

    for line in out.splitlines():
        parts = re.split(r"\s+", line.strip())
        if len(parts) >= 2:
            return _parse_int(parts[0]), _parse_int(parts[1])

    return None, None


def get_group_limits(user: str):
    """
    Return GrpJobs limits for all Slurm associations of the user.
    """
    out = _run(f"sacctmgr show assoc where user={user} format=GrpJobs -n -P")

    if not out:
        return None

    limits = []
    for line in out.splitlines():
        value = line.split("|", 1)[0].strip()
        limits.append(_parse_int(value))

    return min(limits) if len(limits) else None


def compute_max_blocks(safety_factor: float = 0.8, fallback: int = 100):
    """Determine safe maximum of submittable jobs as follows:
    max_blocks <= min(
        user running job limit,
        user submit limit - current submitted jobs,
        QoS running job limit,
        QoS submit limit - current submitted jobs,
    )
    """
    user = getpass.getuser()

    current_jobs = get_current_jobs(user)

    user_max_jobs, user_max_submit = get_user_limits(user)

    qos = get_user_qos(user)
    qos_max_jobs, qos_max_submit = (None, None)
    if qos:
        qos_max_jobs, qos_max_submit = get_qos_limits(qos)
        
    group_max_jobs = get_group_limits(user)

    candidates = []

    if user_max_jobs is not None:
        candidates.append(user_max_jobs)

    if qos_max_jobs is not None:
        candidates.append(qos_max_jobs)

    if user_max_submit is not None:
        candidates.append(max(user_max_submit - current_jobs, 0))

    if qos_max_submit is not None:
        candidates.append(max(qos_max_submit - current_jobs, 0))
    
    if group_max_jobs is not None:
        candidates.append(group_max_jobs)

    if not candidates:
        return max(fallback - current_jobs, 1)

    max_blocks = min(candidates)

    # safety margin
    max_blocks = max(1, int(max_blocks * safety_factor))

    return max_blocks
