"""
PARSL Runner Adaptor
"""

import os

import parsl
from parsl.app.app import bash_app
from parsl.configs.local_threads import config

from parsl.data_provider.files import File


from sustainablecompetition.benchmarkadaptors.abstractinstance import AbstractInstanceAdaptor
from sustainablecompetition.infrastructureadaptors.abstractrunner import AbstractRunner
from sustainablecompetition.benchmarkatoms import Job, Result
from sustainablecompetition.infrastructureadaptors.executionwrapper import AbstractExecutionWrapper
from sustainablecompetition.solveradaptors.abstractsolver import AbstractSolverAdaptor


@bash_app
def runsolver(wrapper: AbstractExecutionWrapper, inputs, outputs):
    """
    Run the solver with the given input and output files.
    """
    wrapper_bin, solver_bin, instance_file = inputs
    tool_output, solver_output, system_output = outputs

    wrapper.set_outputs(tool_output.filepath, solver_output.filepath)
    wrapper_args = " ".join(wrapper.get_command_args())

    return f"""
    # stop eagerly on error
    set -e
    
    # create output directories if they do not exist
    mkdir -p $(dirname "{tool_output.filename}")
    mkdir -p $(dirname "{solver_output.filename}")

    # ensure executable flags are set, since files may be fetched via HTTP etc.:
    chmod +x "{wrapper_bin.filepath}" 
    chmod +x "{solver_bin.filepath}"
    
    # log system information
    uname -a > "{system_output.filepath}"
    lscpu >> "{system_output.filepath}"
    free -h >> "{system_output.filepath}"
    df -h >> "{system_output.filepath}"
    "{wrapper_bin.filepath}" --version >> "{system_output.filepath}" || true

    # run the solver
    "{wrapper_bin.filepath}" {wrapper_args} "{solver_bin.filepath}" "{instance_file.filepath}"
    """


class ParslRunner(AbstractRunner):
    """
    Use parsl to run jobs on various infrastructures.
    """

    def __init__(
        self, rootdir: str, solver_adaptor: AbstractSolverAdaptor, instance_adaptor: AbstractInstanceAdaptor, execution_wrapper: AbstractExecutionWrapper
    ):
        super().__init__(solver_adaptor=solver_adaptor, instance_adaptor=instance_adaptor, execution_wrapper=execution_wrapper)
        parsl.load(config)
        self.futures = []
        self.rootdir = rootdir
        self.logsdir = f"{self.rootdir}/logs"
        os.makedirs(self.logsdir, exist_ok=True)

    def submit(self, job: Job):
        """
        Submit a function to the process pool.
        Return an id for identification of the process future.
        """
        super().submit(job)  # this marks the job as submitted
        job.mark_running()  # mark as running immediately upon submission is a workaround. TODO: introduce proper monitoring of parsl jobs
        # wrap input files as parsl File objects
        wrapper_bin = File(self.execution_wrapper.get_binary_path())
        solver_bin = File(self.solver_adaptor.get_path(job.solver_id))
        instance_file = File(self.instance_adaptor.get_path(job.benchmark_id))
        # wrap output files as parsl File objects
        output_root = f"{self.logsdir}/{job.solver_id}/{job.benchmark_id}"
        tool_output = File(f"{output_root}.log")
        solver_output = File(f"{output_root}.out")
        system_output = File(f"{output_root}.system")
        # set execution wrapper resource limits
        self.execution_wrapper.set_resource_limits(cputimelimit=job.timelimit, memorylimit=job.memlimit)
        runsolver_future = runsolver(
            self.execution_wrapper,
            inputs=[wrapper_bin, solver_bin, instance_file],
            outputs=[tool_output, solver_output, system_output],
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
