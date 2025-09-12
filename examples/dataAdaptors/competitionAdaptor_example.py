# simple example reading from the competition 2024 csv file and printing some things in stdout
import importlib.resources
from sustainablecompetition.dataadaptors.competition_dataadaptor import CompetitionDataAdaptor
from sustainablecompetition.dataadaptors.sqlite_dataadaptor import SqlDataAdaptor


db_path = importlib.resources.files("sustainablecompetition.data").joinpath("sustainablecompetition.db")

cp_adaptor = CompetitionDataAdaptor.from_competition_csv("examples/dataAdaptors/sat/main2024.csv", source_name="main2024", database_path=db_path)
db_adaptor = SqlDataAdaptor(db_path)

solvers = db_adaptor.get_competition_solver_hash("main2024")

print(cp_adaptor.get_performances(solver_hash=solvers[-1]))
print(cp_adaptor.perfs)
print(cp_adaptor.solvers)
