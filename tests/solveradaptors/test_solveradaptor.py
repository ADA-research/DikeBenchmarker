from DikeBenchmarker.benchmarkatoms import SolverResult
from DikeBenchmarker.solveradaptors.solveradaptor import SolverAdaptor


def _write(tmp_path, name, content):
    path = tmp_path / name
    path.write_text(content)
    return str(path)


def test_parse_result_missing_file(tmp_path):
    result = SolverAdaptor().parse_result(str(tmp_path / "missing.out"))
    assert result.state == SolverResult.State.ERROR
    assert result.detail == "no solver output"


def test_parse_result_sat(tmp_path):
    outfile = _write(tmp_path, "sat.out", "c comment\ns SATISFIABLE\n")
    result = SolverAdaptor().parse_result(outfile)
    assert result.state == SolverResult.State.SAT
    assert not result.has_error


def test_parse_result_unsat(tmp_path):
    outfile = _write(tmp_path, "unsat.out", "s UNSATISFIABLE\n")
    result = SolverAdaptor().parse_result(outfile)
    assert result.state == SolverResult.State.UNSAT


def test_parse_result_unknown(tmp_path):
    outfile = _write(tmp_path, "unknown.out", "s UNKNOWN\n")
    result = SolverAdaptor().parse_result(outfile)
    assert result.state == SolverResult.State.UNKNOWN


def test_parse_result_unexpected_verdict_is_error(tmp_path):
    outfile = _write(tmp_path, "garbled.out", "s GARBLED\n")
    result = SolverAdaptor().parse_result(outfile)
    assert result.state == SolverResult.State.ERROR
    assert result.detail == "GARBLED"


def test_parse_result_no_verdict_line_is_error(tmp_path):
    outfile = _write(tmp_path, "empty.out", "c nothing useful here\n")
    result = SolverAdaptor().parse_result(outfile)
    assert result.state == SolverResult.State.ERROR
    assert result.detail == "no solver verdict"
