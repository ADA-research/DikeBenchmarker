# simple example reading from the database the data corresponding to a specific solver and printing it to stdout
import importlib.resources
from sustainablecompetition.dataadaptors.sqlite_dataadaptor import SqlDataAdaptor

db_path = importlib.resources.files("sustainablecompetition.data").joinpath("sustainablecompetition.db")

db_adaptor = SqlDataAdaptor(db_path)
competition_env_hash = db_adaptor.get_competition_env_hash("main2024")
print("the environmene on which the main track os sat competiiton 2024 ran:")
print(db_adaptor.get_environments([competition_env_hash]))
print("the hashs of the solvers from the main track 2024:")
print(db_adaptor.get_competition_solver_hash("main2024"))