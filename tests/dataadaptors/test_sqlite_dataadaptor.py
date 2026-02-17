import sys
import pytest
import polars as pl
import importlib.resources
from sustainablecompetition.dataadaptors.sqlite_dataadaptor import SqlDataAdaptor


@pytest.fixture
def db_path():
    # Use importlib.resources to get the path to the test database
    with importlib.resources.files("sustainablecompetition.data.db").joinpath("sustainablecompetition.db") as db_file:
        return str(db_file)


@pytest.fixture
def adaptor(db_path):
    return SqlDataAdaptor(db_path)


def test_get_performances(adaptor,db_path):
    print(db_path)
    # Test with all optional arguments
    df = adaptor.get_performances(inst_hash="00d1fe07ab948b348bb3fb423b1ef40d", solver_id="AMSAT_main2024", env_id="starexec2024")
    assert isinstance(df, pl.DataFrame)
    assert not df.is_empty()

    # Test with no arguments (should return all performances)
    df_all = adaptor.get_performances()
    assert isinstance(df_all, pl.DataFrame)


def test_get_competition_env(adaptor):
    env_id = adaptor.get_competition_env("main2024")
    assert env_id is not None
    assert isinstance(env_id, str)


def test_get_competition_solver_id(adaptor):
    # Test with solver_name
    print(adaptor.database_path)
    solver_id = adaptor.get_competition_solver_id("main2024", solver_name="AMSAT")
    assert solver_id is not None
    assert isinstance(solver_id, str)

    # Test without solver_name (should return a list)
    solver_ides = adaptor.get_competition_solver_id("main2024")
    assert isinstance(solver_ides, list)
    assert all(isinstance(h, str) for h in solver_ides)


def test_get_environments(adaptor):
    df = adaptor.get_environments(["starexec2024", "starexec2022"])
    assert isinstance(df, pl.DataFrame)
    assert not df.is_empty()


def test_get_instances(adaptor):
    df = adaptor.get_instances(["27f381d4d67c90c8c6a6a186cd51e94a", "28674e12b109f3b3e2967e5770184def"])
    assert isinstance(df, pl.DataFrame)
    assert not df.is_empty()


def test_get_solvers(adaptor):
    df = adaptor.get_solvers(["AMSAT_main2024", "IsaSAT_main2024"])
    assert isinstance(df, pl.DataFrame)
    assert not df.is_empty()


def test_get_all_instance_ids(adaptor):
    inst_ids = adaptor.get_all_instance_ids()
    assert isinstance(inst_ids, list)
    assert all(isinstance(i, str) for i in inst_ids)


def test_get_all_solver_ids(adaptor):
    solver_ids = adaptor.get_all_solver_ids()
    assert isinstance(solver_ids, list)
    assert all(isinstance(i, str) for i in solver_ids)
