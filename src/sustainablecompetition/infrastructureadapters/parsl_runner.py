"""
PARSL Runner Adapter
"""

import os

import parsl
from parsl.app.app import bash_app
from parsl.configs.local_threads import config

from parsl.data_provider.files import File


from sustainablecompetition.benchmarkadapters.abstractinstance import AbstractInstanceAdapter
from sustainablecompetition.infrastructureadapters.abstractrunner import AbstractRunner
from sustainablecompetition.benchmarkatoms import Job, Result
from sustainablecompetition.infrastructureadapters.executionwrapper import AbstractExecutionWrapper
from sustainablecompetition.solveradapters.abstractsolver import AbstractSolverAdapter


class ParslRunner(AbstractRunner):
    """
    Use parsl to run jobs on various infrastructures.
    """

    def __init__(
        self, rootdir: str, solver_adapter: AbstractSolverAdapter, instance_adapter: AbstractInstanceAdapter, execution_wrapper: AbstractExecutionWrapper
    ):
        super().__init__(solver_adapter=solver_adapter, instance_adapter=instance_adapter, execution_wrapper=execution_wrapper)
        parsl.load(config)
        self.futures = []
        self.rootdir = rootdir
        self.logsdir = f"{self.rootdir}/logs"
        os.makedirs(self.logsdir, exist_ok=True)

    @bash_app
    def runsolver(self, wrapper: AbstractExecutionWrapper, inputs, outputs):
        """
        Run the solver with the given input and output files.
        """
        wrapper_bin = inputs[0]
        solver_bin = inputs[1]
        instance_file = inputs[2]
        tool_output = outputs[0]
        solver_output = outputs[1]

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

        "{wrapper_bin.filepath}" {wrapper_args} "{solver_bin.filepath}" "{instance_file.filepath}"
        """

    def submit(self, job: Job):
        """
        Submit a function to the process pool.
        Return an id for identification of the process future.
        """
        super().submit(job)  # this marks the job as submitted
        job.mark_running()  # mark as running immediately upon submission is a workaround. TODO: introduce proper monitoring of parsl jobs
        wrapper_bin = File(self.execution_wrapper.get_binary_path())
        solver_bin = File(self.solver_adapter.get_path(job.solver_id))
        instance_file = File(self.instance_adapter.get_path(job.benchmark_id))
        inputs = [wrapper_bin, solver_bin, instance_file]
        output_root = f"{self.logsdir}/{job.solver_id}/{job.benchmark_id}"
        self.execution_wrapper.set_resource_limits(cputimelimit=job.timelimit, memorylimit=job.memlimit)
        runsolver_future = self.runsolver(self.execution_wrapper, inputs=inputs, outputs=[f"{output_root}.log", f"{output_root}.out"])
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
        # TODO: parse result files for runtime, result, status, etc.
        runtime = 0  # placeholder
        job.set_finished()
        return Result(job, runtime, 0)

    def cancel(self, job):
        return super().cancel(job)
