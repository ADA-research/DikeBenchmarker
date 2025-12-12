"""
Some basic Parsl configurations for demonstration and testing purposes.
"""

from parsl import ThreadPoolExecutor
from parsl.config import Config
from parsl.executors import HighThroughputExecutor

# needed by laptop config
from parsl.providers import LocalProvider
from parsl.addresses import address_by_hostname

# needed by slurm config
from parsl.providers import SlurmProvider
from parsl.launchers import SrunLauncher


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
    jobname: str = "benchmark_job",
    exclusive: bool = True,
    tasks_per_node: int = None,
    mem_per_node: int = None,  # in MB; or leave None to skip
    nodes_per_block: int = 1,
    init_blocks: int = 1,
    min_blocks: int = 1,
    max_blocks: int = 100,
    walltime: str = "02:00:00",
    worker_init: str = """# Load your environment here""",
) -> Config:
    """Create a Parsl config for SLURM-managed clusters."""
    scheduler_opts = [f"#SBATCH --job-name={jobname}"]
    if account:
        scheduler_opts.append(f"#SBATCH --account={account}")
    if mem_per_node:
        scheduler_opts.append(f"#SBATCH --mem={mem_per_node}")
    if exclusive:
        scheduler_opts.append("#SBATCH --exclusive")
    if tasks_per_node:
        scheduler_opts.append(f"#SBATCH --ntasks-per-node={tasks_per_node}")

    return Config(
        executors=[
            HighThroughputExecutor(
                label=f"{jobname}",
                address=address_by_hostname(),
                # Worker layout on each node:
                cores_per_worker=1,  # one worker per core by default
                max_workers_per_node=1,
                worker_debug=True,
                provider=SlurmProvider(
                    partition=partition,
                    nodes_per_block=nodes_per_block,
                    init_blocks=init_blocks,
                    min_blocks=min_blocks,
                    max_blocks=max_blocks,
                    walltime=walltime,
                    launcher=SrunLauncher(overrides=""),  # use srun to launch
                    worker_init=worker_init,
                    scheduler_options="\n".join(scheduler_opts),
                    cmd_timeout=120,
                ),
            )
        ],
        strategy="simple",  # allow Parsl to scale blocks up/down
    )
