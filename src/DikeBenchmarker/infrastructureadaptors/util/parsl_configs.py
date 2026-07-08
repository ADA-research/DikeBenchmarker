"""
Some basic Parsl configurations for demonstration and testing purposes.
"""

import os

from parsl import ThreadPoolExecutor
from parsl.config import Config
from parsl.executors import HighThroughputExecutor

# needed by laptop config
from parsl.providers import LocalProvider
from parsl.addresses import address_by_hostname

# needed by slurm config
from parsl.providers import SlurmProvider
from parsl.launchers import SimpleLauncher


def make_local_processes(n: int = 8) -> Config:
    """
    Launches a single block limited to $n processes with each worker using 1 core.
    """
    return Config(
        executors=[
            HighThroughputExecutor(
                label="local_processes",
                max_workers_per_node=n,
                provider=LocalProvider(init_blocks=1, min_blocks=n, max_blocks=1),
            )
        ]
    )


def make_local_threads(n: int = 8) -> Config:
    """
    Launches a single block limited to $n threads with each worker using 1 core.
    """
    return Config(
        executors=[ThreadPoolExecutor(label="local_threads", max_threads=n)],
        strategy=None,
    )


def make_slurm_config(
    partition: str = "compute",
    account: str = None,  # your account name or None to skip
    reservation: str = None,  # SLURM reservation name or None to skip
    jobname: str = "benchmark_job",
    exclusive: bool = True,
    tasks_per_node: int = None,
    nodes_per_block: int = 1,
    init_blocks: int = 0,
    min_blocks: int = 0,
    max_blocks: int = 100,
    walltime_seconds: int = 172800,  # two days in seconds (default)
    worker_init: str = """# Load your environment here""",
    strategy: str = "htex_auto_scale",
    runinfo_root: str = "runinfo",
    debug: bool = False,
) -> Config:
    """Create a Parsl config for SLURM-managed clusters."""
    scheduler_opts = [f"#SBATCH --job-name={jobname}", "#SBATCH --no-requeue"]
    if account:
        scheduler_opts.append(f"#SBATCH --account={account}")
    if reservation:
        scheduler_opts.append(f"#SBATCH --reservation={reservation}")
    if exclusive:
        scheduler_opts.append("#SBATCH --exclusive")
    if tasks_per_node:
        scheduler_opts.append(f"#SBATCH --ntasks-per-node={tasks_per_node}")

    formatted_walltime = f"{walltime_seconds // 3600:02d}:{(walltime_seconds % 3600) // 60:02d}:{walltime_seconds % 60:02d}"

    # Every author controller starts from the same shared dike working
    # directory, so parsl's default run_dir ("runinfo") is shared across all of
    # them. parsl picks the next runinfo/NNN by globbing the existing dirs and
    # then makedirs()-ing max+1, which is not atomic: when many controllers
    # start at once they choose the SAME number and all but one crash with
    # FileExistsError. Give each controller its own run_dir so the numbered
    # rundirs can never collide. We key on SLURM_JOB_ID *and* jobname: separate
    # master jobs differ by job id, while several masters co-hosted in ONE job
    # (single-node combined launch) share a job id and are disambiguated by
    # their per-solver jobname. Falls back to jobname off-SLURM.
    # runinfo_root places these per-controller rundirs next to the caller's
    # output/log directory.
    run_dir = os.path.join(runinfo_root, f"{os.environ.get('SLURM_JOB_ID', 'local')}-{jobname}")

    return Config(
        run_dir=run_dir,
        executors=[
            HighThroughputExecutor(
                label=f"{jobname}",
                address=address_by_hostname(),
                # Worker layout on each node:
                cores_per_worker=1,  # number of cores per worker
                max_workers_per_node=tasks_per_node or 1,  # number of workers per node
                # 'debug' (set from the yml) turns on parsl's per-worker/manager
                # debug logs (run_dir/<block>/manager.log, worker_*.log).
                worker_debug=debug,
                provider=SlurmProvider(
                    partition=partition,
                    nodes_per_block=nodes_per_block,
                    init_blocks=init_blocks,
                    min_blocks=min_blocks,
                    max_blocks=max_blocks,
                    walltime=formatted_walltime,
                    launcher=SimpleLauncher(),
                    worker_init=worker_init,
                    scheduler_options="\n".join(scheduler_opts),
                    cmd_timeout=120,
                ),
            )
        ],
        # 'htex_auto_scale' (unlike 'simple') also scales IDLE worker blocks back in during the run
        # 'simple' only releases blocks once the executor has zero outstanding tasks
        # idle blocks are reclaimed after Config.max_idletime (default 120 s).
        # A second/small master competing for a busy reservation should use
        # 'simple': htex_auto_scale otherwise reclaims blocks it cannot re-acquire
        # and kills mid-task managers, whose tasks resubmit forever on 'loss of
        # manager' and never complete.
        strategy=strategy,
    )
