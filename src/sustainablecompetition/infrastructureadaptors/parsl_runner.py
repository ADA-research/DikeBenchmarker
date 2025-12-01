"""
PARSL Runner Adaptor
"""

import os

import parsl
from parsl.app.app import bash_app
from parsl.configs.local_threads import config as default_config
from parsl.config import Config

from parsl.data_provider.files import File


from sustainablecompetition.benchmarkadaptors.abstractinstance import AbstractInstanceAdaptor
from sustainablecompetition.infrastructureadaptors.abstractrunner import AbstractRunner
from sustainablecompetition.benchmarkatoms import Job, Result
from sustainablecompetition.solveradaptors.executionwrapper import ExecutionWrapper
from sustainablecompetition.solveradaptors.solveradaptor import SolverAdaptor


@bash_app
def runsolver(serialized_wrapper: dict, serialized_solver: dict, wrapper_id: str, solver_id: str, inputs: list[File], outputs: list[File]):
    """Run the solver with the given input and output files."""

    wrapper_bin, solver_bin, instance_file = inputs
    system_output, tool_output, solver_output, cert_output = outputs

    wrapper = ExecutionWrapper.from_dict(serialized_wrapper)
    solver = SolverAdaptor.from_dict(serialized_solver)

    solve_cmd = solver.format_command(solver_id, solver_bin.filepath, instance_file.filepath, cert_output.filepath)
    wrapper_cmd = wrapper.format_command(wrapper_id, wrapper_bin.filepath, solve_cmd, tool_output.filepath, solver_output.filepath)

    return f"""
    # stop eagerly on error
    set -e
    set -x  # enable debug output to see which commands are executed
    
    for f in "{system_output.filepath}" "{tool_output.filepath}" "{solver_output.filepath}" "{cert_output.filepath}"; do
        touch "$f"
    done

    # ensure executable flags are set, since files may be fetched via HTTP etc.:
    chmod +x "{wrapper_bin.filepath}" "{solver_bin.filepath}"
    
    # log system information
    uname -a; echo; lscpu; echo; free -h; echo; df -h; echo > "{system_output.filepath}"
    "{wrapper_bin.filepath}" --version >> "{system_output.filepath}"
    echo "{wrapper_cmd}" >> "{system_output.filepath}"

    # run the solver
    {wrapper_cmd}
    """


class ParslRunner(AbstractRunner):
    """Use parsl to run jobs on various infrastructures."""

    def __init__(
        self,
        rootdir: str,
        solver_adaptor: SolverAdaptor,
        instance_adaptor: AbstractInstanceAdaptor,
        execution_wrapper: ExecutionWrapper,
        parsl_config: Config = default_config,
    ):
        super().__init__(solver_adaptor, instance_adaptor, execution_wrapper)
        parsl.load(parsl_config)
        self.futures = []
        self.rootdir = rootdir
        self.logsdir = f"{self.rootdir}/logs"
        os.makedirs(self.logsdir, exist_ok=True)

    def __del__(self):
        parsl.dfk().cleanup()
        parsl.clear()

    def submit(self, job: Job):
        """
        Submit a function to the process pool.
        Return an id for identification of the process future.
        """
        super().submit(job)  # this marks the job as submitted
        job.mark_running()  # mark as running immediately (workaround) TODO: proper monitoring of PARSL jobs
        output_root = f"{self.logsdir}/{job.solver_id}/{job.benchmark_id}"
        os.makedirs(os.path.dirname(output_root), exist_ok=True)

        # set execution wrapper resource limits
        self.execution_wrapper.set_resource_limits(cputimelimit=job.timelimit, memorylimit=job.memlimit)
        runsolver_future = runsolver(
            self.execution_wrapper.to_dict(),
            self.solver_adaptor.to_dict(),
            "runsolver",
            job.solver_id,
            inputs=[
                File(self.execution_wrapper.get_binary("runsolver")),
                File(self.solver_adaptor.get_binary(job.solver_id)),
                File(self.instance_adaptor.get_path(job.benchmark_id)),
            ],
            outputs=[File(output_root + ext) for ext in [".log", ".out", ".system", ".cert"]],
        )
        self.futures.append(runsolver_future)
        job.external_id = len(self.futures) - 1

    def completed(self, job: Job) -> Result:
        """
        Return the runtime result for the solver/instance pair.
        """
        extid = job.external_id
        job_future = self.futures[extid]
        if not job_future.done():
            return None

        if job_future.exception() is not None:
            print(f"Job {job.solver_id} on {job.benchmark_id} failed with exception: {job_future.exception()}")
            raise job_future.exception()

        output_root = f"{self.logsdir}/{job.solver_id}/{job.benchmark_id}"
        tool_output, solver_output, system_output = [f"{output_root}.log", f"{output_root}.out", f"{output_root}.system"]

        resource_usage = self.execution_wrapper.parse_result(tool_output)
        solver_result = self.solver_adaptor.parse_result(solver_output)
        with open(system_output, "r") as f:
            system_result = f.read()

        job.set_finished()
        return Result(job, resource_usage["cputime"], resource_usage["memory"])

    def cancel(self, job):
        return super().cancel(job)
