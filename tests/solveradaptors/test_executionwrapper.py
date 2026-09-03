from DikeBenchmarker.benchmarkatoms import ResourceResult
from DikeBenchmarker.solveradaptors.executionwrapper import ExecutionWrapper


def _write(tmp_path, name, content):
    path = tmp_path / name
    path.write_text(content)
    return str(path)


def test_parse_result_missing_wrapper_file(tmp_path):
    result = ExecutionWrapper().parse_result(str(tmp_path / "missing.var"), str(tmp_path / "watcher.out"))
    assert result.state == ResourceResult.State.NONE
    assert result.detail == "no wrapper output"


def test_parse_result_parses_metrics_without_watcher_file(tmp_path):
    wrapper = _write(tmp_path, "wrapper.var", "WCTIME=12.5\nCPUTIME=10.0\nMAXVM=2048\n")
    result = ExecutionWrapper().parse_result(wrapper, str(tmp_path / "missing_watcher.out"))
    assert result.state == ResourceResult.State.SUCCESS
    assert result.cputime == 10.0
    assert result.walltime == 12.5
    assert result.memory == 2.0
    assert result.detail == "no watcher output"


def test_parse_result_wrapper_timeout_flag(tmp_path):
    wrapper = _write(tmp_path, "wrapper.var", "TIMEOUT=true\n")
    result = ExecutionWrapper().parse_result(wrapper, str(tmp_path / "missing_watcher.out"))
    assert result.state == ResourceResult.State.TIMEOUT


def test_parse_result_wrapper_memout_flag(tmp_path):
    wrapper = _write(tmp_path, "wrapper.var", "MEMOUT=true\n")
    result = ExecutionWrapper().parse_result(wrapper, str(tmp_path / "missing_watcher.out"))
    assert result.state == ResourceResult.State.MEMOUT


def test_parse_result_watcher_memory_exceeded_overrides_wrapper(tmp_path):
    wrapper = _write(tmp_path, "wrapper.var", "CPUTIME=1.0\n")
    watcher = _write(tmp_path, "watcher.out", "Maximum memory exceeded\n")
    result = ExecutionWrapper().parse_result(wrapper, watcher)
    assert result.state == ResourceResult.State.MEMOUT
    assert result.detail == "runsolver memory limit exceeded"
    assert result.cputime == 1.0


def test_parse_result_watcher_sigxcpu(tmp_path):
    wrapper = _write(tmp_path, "wrapper.var", "")
    watcher = _write(tmp_path, "watcher.out", "Child ended because it received signal 24 (SIGXCPU)\n")
    result = ExecutionWrapper().parse_result(wrapper, watcher)
    assert result.state == ResourceResult.State.TIMEOUT
    assert result.detail == "cpu time limit exceeded (SIGXCPU)"


def test_parse_result_watcher_sigkill(tmp_path):
    wrapper = _write(tmp_path, "wrapper.var", "")
    watcher = _write(tmp_path, "watcher.out", "Child ended because it received signal 9 (SIGKILL)\n")
    result = ExecutionWrapper().parse_result(wrapper, watcher)
    assert result.state == ResourceResult.State.ERROR
    assert result.detail == "killed (SIGKILL via exit 9)"


def test_parse_result_watcher_exit_code_137_is_external_kill(tmp_path):
    wrapper = _write(tmp_path, "wrapper.var", "")
    watcher = _write(tmp_path, "watcher.out", "Child status: 137\n")
    result = ExecutionWrapper().parse_result(wrapper, watcher)
    assert result.state == ResourceResult.State.ERROR
    assert result.detail == "killed (SIGKILL via exit 137)"


def test_parse_result_watcher_nonzero_exit_code(tmp_path):
    wrapper = _write(tmp_path, "wrapper.var", "")
    watcher = _write(tmp_path, "watcher.out", "Child status: 20\n")
    result = ExecutionWrapper().parse_result(wrapper, watcher)
    assert result.state == ResourceResult.State.SUCCESS
    assert result.detail == "nonzero exit (code 20)"


def test_parse_result_watcher_success(tmp_path):
    wrapper = _write(tmp_path, "wrapper.var", "CPUTIME=0.5\n")
    watcher = _write(tmp_path, "watcher.out", "Child status: 0\n")
    result = ExecutionWrapper().parse_result(wrapper, watcher)
    assert result.state == ResourceResult.State.SUCCESS
    assert result.detail is None
    assert not result.has_error
