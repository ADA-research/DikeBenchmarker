from abc import ABC, abstractmethod

__all__ = ["AbstractPerformanceModel"]


class AbstractPerformanceModel(ABC):
    """A performance model learning from 4 input files (currently, corresponding to the 4 tables in our future database)"""

    @abstractmethod
    def train(self, X, Y):
        """train the model"""

    @abstractmethod
    def predict(self, x_input):
        """predicts stuff"""
