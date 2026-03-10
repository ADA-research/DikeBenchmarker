import pathlib
import os
import lzma

import pytest
from requests import HTTPError

from DikeBenchmarker.benchmarkadaptors.satinstance import SATInstanceAdaptor


INSTANCE_HASH = "001304ba2e4e8adbd179aa3d8acb697b"
INSTANCE_SIZE = 15136 + 80


def test_get_instance(tmp_path: pathlib.Path):
    adaptor = SATInstanceAdaptor(tmp_path)
    local_path = adaptor.get_path(INSTANCE_HASH)
    assert os.path.isfile(local_path)

    with lzma.open(local_path, "rb") as fd:
        size = len(fd.read())
        assert size == INSTANCE_SIZE


def test_registry_cache(tmp_path: pathlib.Path):
    adaptor = SATInstanceAdaptor(tmp_path)
    local_path = adaptor.get_path(INSTANCE_HASH)
    assert local_path == adaptor.get_local_path(INSTANCE_HASH)


def test_incorrect_id(tmp_path: pathlib.Path):
    adaptor = SATInstanceAdaptor(tmp_path)
    with pytest.raises(HTTPError) as e:
        adaptor.get_path(INSTANCE_HASH * 10)
        f: HTTPError = e
        assert f.errno == 404
