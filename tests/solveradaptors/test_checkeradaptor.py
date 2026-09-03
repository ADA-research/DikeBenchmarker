from DikeBenchmarker.benchmarkatoms import CheckerResult
from DikeBenchmarker.solveradaptors.checkeradaptor import CheckerAdaptor


def _write(tmp_path, name, content):
    path = tmp_path / name
    path.write_text(content)
    return str(path)


def test_parse_result_missing_trimmer_file(tmp_path):
    result = CheckerAdaptor().parse_result(str(tmp_path / "no_trimmer.out"), str(tmp_path / "checker.out"))
    assert result.state == CheckerResult.State.ERROR
    assert result.detail == "no trimmer output"


def test_parse_result_trimmer_memout(tmp_path):
    trimmer = _write(tmp_path, "trimmer.out", "Ran out of memory\n")
    result = CheckerAdaptor().parse_result(trimmer, str(tmp_path / "checker.out"))
    assert result.state == CheckerResult.State.ERROR
    assert result.detail == "trimmer internal memout"


def test_parse_result_trimmer_no_verdict(tmp_path):
    trimmer = _write(tmp_path, "trimmer.out", "c nothing useful\n")
    result = CheckerAdaptor().parse_result(trimmer, str(tmp_path / "checker.out"))
    assert result.state == CheckerResult.State.ERROR
    assert result.detail == "trimmer no verdict"


def test_parse_result_trimmer_timeout(tmp_path):
    trimmer = _write(tmp_path, "trimmer.out", "s TIMEOUT\n")
    result = CheckerAdaptor().parse_result(trimmer, str(tmp_path / "checker.out"))
    assert result.state == CheckerResult.State.ERROR
    assert result.detail == "trimmer internal timeout"


def test_parse_result_missing_checker_file(tmp_path):
    trimmer = _write(tmp_path, "trimmer.out", "s VERIFIED\n")
    result = CheckerAdaptor().parse_result(trimmer, str(tmp_path / "no_checker.out"))
    assert result.state == CheckerResult.State.ERROR
    assert "no checker output" in result.detail


def test_parse_result_verified(tmp_path):
    trimmer = _write(tmp_path, "trimmer.out", "s VERIFIED\n")
    checker = _write(tmp_path, "checker.out", "s VERIFIED\n")
    result = CheckerAdaptor().parse_result(trimmer, checker)
    assert result.state == CheckerResult.State.VERIFIED
    assert not result.has_error


def test_parse_result_unverified(tmp_path):
    trimmer = _write(tmp_path, "trimmer.out", "s VERIFIED\n")
    checker = _write(tmp_path, "checker.out", "s NOT VERIFIED\n")
    result = CheckerAdaptor().parse_result(trimmer, checker)
    assert result.state == CheckerResult.State.UNVERIFIED


def test_parse_result_checker_no_verdict_is_unknown(tmp_path):
    trimmer = _write(tmp_path, "trimmer.out", "s VERIFIED\n")
    checker = _write(tmp_path, "checker.out", "c nothing useful\n")
    result = CheckerAdaptor().parse_result(trimmer, checker)
    assert result.state == CheckerResult.State.UNKNOWN
