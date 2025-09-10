import polars as pl
from sklearn.ensemble import RandomForestRegressor

## needed only for the test at the end of the file
from sustainablecompetition.dataadaptors.csv_dataadaptor import CsvDataAdaptor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error


class PerformanceModel:
    """A performance model learning from 4 input files (currently, corresponding to the 4 tables in our future database)

    Raises:
        ValueError: _description_

    Returns:
        _type_: _description_
    """

    def __init__(self):
        """Initialises the model

        Args:
            should take the RF parameters

        """
        self.model = RandomForestRegressor(n_estimators=100, random_state=42)

    def train(self, X, Y):
        """train the model
        for now very basic but could be better tailored in the future (handling saturated right tail for example)
        """
        self.model.fit(X, Y)

    def predict(self, x_input):
        """predicts stuff, for now simple but could be refined

        Args:
            x_input (dataframe): _description_

        Raises:
            ValueError: _description_

        Returns:
            _type_: _description_
        """

        return self.model.predict(x_input)


if __name__ == "__main__":
    data = CsvDataAdaptor(pl.DataFrame())
    data.get_performances("environments.csv", "instances.csv", "solvers.csv", "performances.csv")
    # Drop hash columns and status, keep only features and perf
    X = data.df.drop(["env_hash", "inst_hash", "solver_hash", "status", "perf"])
    # for this test, also drop non numerical data TODO handle them better
    print(X.columns)
    X = X.drop(["kernel_version", "activated_modules", "cpu_brand", "cpu_model", "solver_name"])
    y_perfs = data.df["perf"].to_numpy()
    y_status = data.df["status"].to_numpy()
    # Initialize
    rf = PerformanceModel()
    X_train, X_test, y_train, y_test = train_test_split(X, y_perfs, test_size=0.2, random_state=42)
    rf.train(X_train, y_train)
    y_pred = rf.predict(X_test)
    mse = mean_squared_error(y_test, y_pred)
    print(f"MSE predict performance: {mse}")
