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
from sustainablecompetition.solveradaptors.checkeradaptor import CheckerAdaptor
from sustainablecompetition.solveradaptors.executionwrapper import ExecutionWrapper
from sustainablecompetition.solveradaptors.solveradaptor import SolverAdaptor


@bash_app
def runsolver(serialized_wrapper: dict, serialized_solver: dict, serialized_checker: dict, wrapper_id: str, solver_id: str, checker_id: str, inputs: list[File], outputs: list[File]):
    """Run the solver with the given input and output files."""

    wrapper_bin, solver_bin, instance_file, trimmer_bin, checker_bin, satchecker_bin = inputs
    out, err, wrapper_out, solver_out, model_out, trimmer_out, checker_out = outputs
    cnf = f"{solver_out.filepath}.cnf"
    cert_out = f"{solver_out.filepath}.cert"

    wrapper = ExecutionWrapper.from_dict(serialized_wrapper)
    solver = SolverAdaptor.from_dict(serialized_solver)
    checker = CheckerAdaptor.from_dict(serialized_checker)

    solve_cmd = solver.format_command(solver_id, solver_bin.filepath, cnf, cert_out)
    wrapper_cmd = wrapper.format_command(wrapper_id, wrapper_bin.filepath, solve_cmd, wrapper_out.filepath, solver_out.filepath)
    proof_checker_cmd = checker.format_command(checker_id, trimmer_bin.filepath, checker_bin.filepath, cnf, cert_out, trimmer_out.filepath, checker_out.filepath)
    model_checker_cmd = checker.format_command("satchecker", satchecker_bin.filepath, "", cnf, solver_out.filepath, "", checker_out.filepath)

    return f"""
    # redirect output and error streams
    exec >"{out.filepath}" 2>"{err.filepath}"

    # stop eagerly on error
    set -e
    set -x  # enable debug output to see which commands are executed
    
    for f in "{wrapper_out.filepath}" "{solver_out.filepath}" "{model_out.filepath}" "{trimmer_out.filepath}" "{checker_out.filepath}"; do
        touch "$f"
    done

    # ensure executable flags are set, since files may be fetched via HTTP etc.:
    chmod +x "{wrapper_bin.filepath}" "{solver_bin.filepath}" "{trimmer_bin.filepath}" "{checker_bin.filepath}" "{satchecker_bin.filepath}"
    
    # log system information
    uname -a; echo; lscpu; echo; free -h; echo; df -h; echo
    "{wrapper_bin.filepath}" --version
    echo "{wrapper_cmd}"
    
    xzcat {instance_file.filepath} > "{cnf}"

    # run the solver
    {wrapper_cmd}
    
    # run the proof/model checker based on the solver output
    if ( grep "s SATISFIABLE" {solver_out.filepath} > /dev/null ); then
        echo "s SATISFIABLE"
        {model_checker_cmd}
    elif ( grep "s UNSATISFIABLE" {solver_out.filepath} > /dev/null ); then
        echo "s UNSATISFIABLE"
        {proof_checker_cmd}
    fi
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
        self.checker_adaptor = CheckerAdaptor()
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
            self.checker_adaptor.to_dict(),
            "runsolver",
            job.solver_id,
            job.checker_id,
            inputs=[
                File(self.execution_wrapper.get_binaries("runsolver")[0]),
                File(self.solver_adaptor.get_binaries(job.solver_id)[0]),
                File(self.instance_adaptor.get_path(job.benchmark_id)),
                File(self.checker_adaptor.get_binaries(job.checker_id)[0]),
                File(self.checker_adaptor.get_binaries(job.checker_id)[1]),
                File(self.checker_adaptor.get_binaries("satchecker")[0]),
            ],
            outputs=[
                File(output_root + ext) for ext in [".out", ".err",".wrapper", ".solver", ".model", ".trimmer", ".checker"]
            ],
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
        out, err, wrapper_out, solver_out, model_out, trimmer_out, checker_out = [ output_root + ext for ext in [".out", ".err",".wrapper", ".solver", ".model", ".trimmer", ".checker"] ]

        resource_usage = self.execution_wrapper.parse_result(wrapper_out)
        solver_result = self.solver_adaptor.parse_result(solver_out)

        job.set_finished()
        return Result(job, resource_usage["cputime"], resource_usage["memory"])

    def cancel(self, job):
        return super().cancel(job)
