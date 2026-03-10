"""PARSL Runner Adaptor."""

import logging
import os

import parsl
from parsl.app.app import bash_app
from parsl.configs.local_threads import config as default_config
from parsl.config import Config

from parsl.data_provider.files import File


from DikeBenchmarker.benchmarkadaptors.abstractinstance import AbstractInstanceAdaptor
from DikeBenchmarker.infrastructureadaptors.abstract_runner import AbstractRunner
from DikeBenchmarker.benchmarkatoms import Job, Result
from DikeBenchmarker.solveradaptors.checkeradaptor import CheckerAdaptor
from DikeBenchmarker.solveradaptors.executionwrapper import ExecutionWrapper
from DikeBenchmarker.solveradaptors.solveradaptor import SolverAdaptor


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
    """Run the solver with the given input and output files.

    All File objects are automatically copied to the remote execution location by parsl.
    The File objects in outputs are created at the remote location and copied back to the local machine after execution.
    The dictionaries are serialized versions of the respective adaptor and wrapper objects which are re-created at the remote location.
    """
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
    cnf = f"{solver_out.filepath}.unpacked.cnf"
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
    uname -a; echo; lscpu; echo; free -h; echo; df -h; echo; ps aux; echo;
    echo "{wrapper_cmd}"

    case "{benchmark_instance.filepath}" in
        *.xz)              xzcat "{benchmark_instance.filepath}" ;;
        *.bz2)             bzcat "{benchmark_instance.filepath}" ;;
        *.gz)              zcat "{benchmark_instance.filepath}" ;;
        *.tar.gz|*.tgz)    tar -xOzf "{benchmark_instance.filepath}" ;;
        *.tar.bz2|*.tbz2)  tar -xOjf "{benchmark_instance.filepath}" ;;
        *.tar.xz|*.txz)    tar -xOJf "{benchmark_instance.filepath}" ;;
        *.tar)             tar -xOf "{benchmark_instance.filepath}" ;;
        *)                 cat "{benchmark_instance.filepath}" ;;
    esac > "{cnf}"

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
        """Initialize the ParslRunner."""
        super().__init__(solver_adaptor, instance_adaptor)
        self.checker_adaptor = CheckerAdaptor()
        self.solver_wrapper = solver_wrapper
        self.checker_wrapper = checker_wrapper
        parsl.load(parsl_config)
        logging.basicConfig(level=logging.WARNING)
        logging.getLogger("parsl").setLevel(logging.WARNING)
        # parsl.set_stream_logger()
        self.futures_map = {}  # maps job uid to future for easy lookup

    def submit(self, job: Job) -> bool:
        """Submit a function to the process pool.

        Return False if the result files already exist (i.e., job already completed in a previous run), otherwise return True.
        """
        if not super().submit(job):
            return False

        job.mark_running()

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
            outputs=[File(job.get_log_prefix() + ext) for ext in [".out", ".err", ".wrapper", ".solver", ".model", ".trimmer", ".checker"]],
        )

        self.futures_map[job.uid] = runsolver_future

        return True

    def completed(self, job: Job) -> Result:
        """Return the runtime result for the solver/instance pair."""
        job_future = self.futures_map[job.uid]
        if not job_future.done():
            return None

        # get output file paths
        output_root = job.get_log_prefix()
        out, err, wrapper_out, solver_out, model_out, trimmer_out, checker_out = [
            output_root + ext for ext in [".out", ".err", ".wrapper", ".solver", ".model", ".trimmer", ".checker"]
        ]

        # cleanup .unpacked.cnf and .cert files if they still exist
        cnf_path = f"{output_root}.solver.unpacked.cnf"
        cert_path = f"{output_root}.solver.cert"
        if os.path.exists(cnf_path):
            os.remove(cnf_path)
        if os.path.exists(cert_path):
            os.remove(cert_path)

        # check for and handle exceptions
        if job_future.exception() is not None:
            print(f"Job {job.solver_id} on {job.benchmark_id} failed with exception: {job_future.exception()}")
            with open(err, "a") as f:
                f.write(f"Job failed with exception: {job_future.exception()}\n")
            job.set_failed(str(job_future.exception()))
            return Result(job, failed=True)

        # mark job as done for future runs
        with open(f"{output_root}.done", "w") as f:
            f.write("")

        resource_usage = self.solver_wrapper.parse_result(wrapper_out)
        solver_result = self.solver_adaptor.parse_result(solver_out)

        job.set_finished()
        return Result(job, resource_usage["cputime"], resource_usage["memory"])

    def cancel(self, job):
        """Cancel a running job."""
        job_future = self.futures_map[job.uid]
        job_future.cancel()
        return super().cancel(job)
