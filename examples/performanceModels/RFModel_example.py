from DikeBenchmarker.performancemodels.randomforestmodel import RandomForestPerformanceModel
import polars as pl
from DikeBenchmarker.dataadaptors.sqlite_dataadaptor import SqlDataAdaptor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error
import importlib.resources


db_path = importlib.resources.files("DikeBenchmarker.data.db").joinpath("sustainablecompetition.db")
db_adaptor = SqlDataAdaptor(db_path)

# gathering my data
main2024_data = db_adaptor.get_performances(env_hash=db_adaptor.get_competition_env_hash("main2024"), filter="no_env_features")
solvers = db_adaptor.get_competition_solver_hash(comp_name="main2024")
kathleen_data = db_adaptor.get_performances(solver_hash=solvers[0], env_hash="597c479a9bc71e9bdc080f1d491b0ac4", filter="no_env_features")
if len(solvers) > 1:
    for solver in solvers[1:]:
        solver_data = db_adaptor.get_performances(solver_hash=solver, env_hash="597c479a9bc71e9bdc080f1d491b0ac4", filter="no_env_features")
        if not solver_data.is_empty():
            kathleen_data = pl.concat([kathleen_data, solver_data], how="align")


# Drop hash columns and status, keep only features and perf
X1 = main2024_data.drop(
    ["env_hash", "inst_hash", "solver_hash", "solver_base", "competition", "status", "perf", "vg_degree_mean", "cg_degree_mean"]
).to_dummies()
print(main2024_data.columns)
y1_perfs = main2024_data["perf"].to_numpy()
# Initialize
rf = RandomForestPerformanceModel()
X1_train, X1_test, y1_train, y1_test = train_test_split(X1, y1_perfs, test_size=0.2, random_state=42)
rf.train(X1_train, y1_train)
y1_pred = rf.predict(X1_test)
mse = mean_squared_error(y1_test, y1_pred)
print(f"MSE predict performance: {mse}")
