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
def runsolver(
    solver_wrapper_id: str,
    solver_wrapper_serialized: dict,
    solver_wrapper_binaries: list[File],
    solver_id: str,
    solver_serialized: dict,
    solver_binaries: list[File],
    checker_id: str,
    checker_serialized: dict,
    checker_binaries: list[File],
    checker_wrapper_id: str,
    checker_wrapper_serialized: dict,
    checker_wrapper_binaries: list[File],
    satchecker_binaries: list[File],
    benchmark_instance: File,
    outputs: list[File],
):
    """Run the solver with the given input and output files."""

    # ensure executable flags are set, since files may be fetched via HTTP etc.:
    for f in solver_wrapper_binaries + solver_binaries + checker_binaries + checker_wrapper_binaries + satchecker_binaries:
        os.chmod(f.filepath, 0o755)

    for f in outputs:
        open(f.filepath, "w").close()

    solver_wrapper_binaries_paths = [f.filepath for f in solver_wrapper_binaries]
    checker_wrapper_binaries_paths = [f.filepath for f in checker_wrapper_binaries]
    solver_binaries_paths = [f.filepath for f in solver_binaries]
    checker_binaries_paths = [f.filepath for f in checker_binaries]
    satchecker_binaries_paths = [f.filepath for f in satchecker_binaries]

    out, err, wrapper_out, solver_out, model_out, trimmer_out, checker_out = outputs
    cnf = f"{benchmark_instance.filepath}.unpacked.cnf"
    cert_out = f"{solver_out.filepath}.cert"

    solver_wrapper = ExecutionWrapper.from_dict(solver_wrapper_serialized)
    solver = SolverAdaptor.from_dict(solver_serialized)
    checker_wrapper = ExecutionWrapper.from_dict(checker_wrapper_serialized)
    checker = CheckerAdaptor.from_dict(checker_serialized)

    solve_cmd = solver.format_command(solver_id, solver_binaries_paths, cnf, cert_out)
    wrapper_cmd = solver_wrapper.format_command(solver_wrapper_id, solver_wrapper_binaries_paths, solve_cmd, wrapper_out.filepath, solver_out.filepath)

    proof_checker_cmd = checker.format_command(checker_id, checker_binaries_paths, cnf, cert_out, trimmer_out.filepath, checker_out.filepath)
    proof_checker_wrapper_cmd = checker_wrapper.format_command(
        checker_wrapper_id,
        checker_wrapper_binaries_paths,
        proof_checker_cmd,
        wrapper_out.filepath + ".checker_wrapper",
        checker_out.filepath + ".checker_wrapped",
    )
    model_checker_cmd = checker.format_command("satchecker", satchecker_binaries_paths, cnf, solver_out.filepath, "", checker_out.filepath)
    return f"""
    # redirect output and error streams
    exec >"{out.filepath}" 2>"{err.filepath}"

    # stop eagerly on error
    set -e
    set -x  # enable debug output to see which commands are executed
    
    # log system information
    uname -a; echo; lscpu; echo; free -h; echo; df -h; echo
    echo "{wrapper_cmd}"
    
    xzcat {benchmark_instance.filepath} > "{cnf}"

    # run the solver
    {wrapper_cmd}
    
    # run the proof/model checker based on the solver output
    if ( grep "s SATISFIABLE" {solver_out.filepath} > /dev/null ); then
        echo "s SATISFIABLE"
        {model_checker_cmd}
    elif ( grep "s UNSATISFIABLE" {solver_out.filepath} > /dev/null ); then
        echo "s UNSATISFIABLE"
        {proof_checker_wrapper_cmd}
    fi
    
    rm -f "{cnf}" "{cert_out}"
    """


class ParslRunner(AbstractRunner):
    """Use parsl to run jobs on various infrastructures."""

    def __init__(
        self,
        solver_adaptor: SolverAdaptor,
        instance_adaptor: AbstractInstanceAdaptor,
        solver_wrapper: ExecutionWrapper,
        checker_wrapper: ExecutionWrapper,
        parsl_config: Config = default_config,
    ):
        super().__init__(solver_adaptor, instance_adaptor)
        self.checker_adaptor = CheckerAdaptor()
        self.solver_wrapper = solver_wrapper
        self.checker_wrapper = checker_wrapper
        parsl.load(parsl_config)
        self.futures = []

    def __del__(self):
        parsl.dfk().cleanup()
        parsl.clear()

    def submit(self, job: Job):
        """
        Submit a function to the process pool.
        Return an id for identification of the process future.
        """
        output_root = job.get_log_prefix()
        os.makedirs(os.path.dirname(output_root), exist_ok=True)

        if os.path.exists(f"{output_root}.done"):
            return

        super().submit(job)  # this marks the job as submitted
        job.mark_running()  # mark as running immediately (workaround) TODO: proper monitoring of PARSL jobs

        runsolver_future = runsolver(
            solver_wrapper_id="runsolver",
            solver_wrapper_serialized=self.solver_wrapper.to_dict(),
            solver_wrapper_binaries=[File(f) for f in self.solver_wrapper.get_binaries("runsolver")],
            solver_id=job.solver_id,
            solver_serialized=self.solver_adaptor.to_dict(),
            solver_binaries=[File(f) for f in self.solver_adaptor.get_binaries(job.solver_id)],
            checker_wrapper_id="runsolver",
            checker_wrapper_serialized=self.checker_wrapper.to_dict(),
            checker_wrapper_binaries=[File(f) for f in self.checker_wrapper.get_binaries("runsolver")],
            checker_id=job.checker_id,
            checker_serialized=self.checker_adaptor.to_dict(),
            checker_binaries=[File(f) for f in self.checker_adaptor.get_binaries(job.checker_id)],
            satchecker_binaries=[File(f) for f in self.checker_adaptor.get_binaries("satchecker")],
            benchmark_instance=File(self.instance_adaptor.get_path(job.benchmark_id)),
            outputs=[File(output_root + ext) for ext in [".out", ".err", ".wrapper", ".solver", ".model", ".trimmer", ".checker"]],
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
            job.set_failed(str(job_future.exception()))
            return Result(job, failed=True)

        output_root = job.get_log_prefix()
        with open(f"{output_root}.done", "w") as f:
            f.write("")

        out, err, wrapper_out, solver_out, model_out, trimmer_out, checker_out = [
            output_root + ext for ext in [".out", ".err", ".wrapper", ".solver", ".model", ".trimmer", ".checker"]
        ]

        resource_usage = self.solver_wrapper.parse_result(wrapper_out)
        solver_result = self.solver_adaptor.parse_result(solver_out)

        job.set_finished()
        return Result(job, resource_usage["cputime"], resource_usage["memory"])

    def cancel(self, job):
        return super().cancel(job)
