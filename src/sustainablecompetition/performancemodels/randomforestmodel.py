from sklearn.ensemble import RandomForestRegressor
from sustainablecompetition.performancemodels.abstractperformancemodel import AbstractPerformanceModel

__all__ = ["RandomForestPerformanceModel"]


class RandomForestPerformanceModel(AbstractPerformanceModel):
    """A performance model learning from 4 input files (currently, corresponding to the 4 tables in our future database)"""

    def __init__(self):
        """Initialises the model

        Args:
            TODO should take the RF parameters

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
