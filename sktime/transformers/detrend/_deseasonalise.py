#!/usr/bin/env python3 -u
# coding: utf-8

__author__ = ["Markus Löning"]
__all__ = [
    "Deseasonaliser",
    "Deseasonalizer",
    "ConditionalDeseasonaliser",
    "ConditionalDeseasonalizer"
]

from warnings import warn

import numpy as np
from sktime.transformers.detrend._base import BaseSeriesToSeriesTransformer
from sktime.utils.seasonality import autocorrelation_seasonality_test
from sktime.utils.validation.forecasting import check_sp, check_y, check_time_index
from statsmodels.tsa.seasonal import seasonal_decompose


class Deseasonaliser(BaseSeriesToSeriesTransformer):
    """A transformer that removes a seasonal and trend components from time series

    Parameters
    ----------
    sp : int, optional (default=1)
        Seasonal periodicity
    model : str {"additive", "multiplicative"}, optional (default="additive")
        Model to use for estimating seasonal component
    """

    def __init__(self, sp=1, model="additive"):
        self.sp = check_sp(sp)
        allowed_models = ("additive", "multiplicative")
        if model not in allowed_models:
            raise ValueError(f"`model` must be one of {allowed_models}, "
                             f"but found: {model}")
        self.model = model
        self._oh_index = None
        self.seasonal_ = None
        super(Deseasonaliser, self).__init__()

    def _set_oh_index(self, y):
        self._oh_index = check_time_index(y.index)

    def _align_seasonal(self, y):
        """Helper function to align seasonal components with y's time index"""
        shift = -(y.index[0] - self._oh_index[0]) % self.sp
        return np.resize(np.roll(self.seasonal_, shift=shift), y.shape[0])

    def fit(self, y, **fit_params):
        y = check_y(y)
        self._set_oh_index(y)
        sp = check_sp(self.sp)
        self.seasonal_ = seasonal_decompose(y, model=self.model, period=sp, filt=None, two_sided=True,
                                            extrapolate_trend=0).seasonal.iloc[:sp]
        self._is_fitted = True
        return self

    def _detrend(self, y, seasonal):
        if self.model == "additive":
            return y - seasonal
        else:
            return y / seasonal

    def _retrend(self, y, seasonal):
        if self.model == "additive":
            return y + seasonal
        else:
            return y * seasonal

    def transform(self, y, **transform_params):
        self.check_is_fitted()
        y = check_y(y)
        seasonal = self._align_seasonal(y)
        return self._detrend(y, seasonal)

    def inverse_transform(self, y, **transform_params):
        self.check_is_fitted()
        y = check_y(y)
        seasonal = self._align_seasonal(y)
        return self._retrend(y, seasonal)

    def update(self, y_new, update_params=False):
        self.check_is_fitted()
        y_new = check_y(y_new)
        self._set_oh_index(y_new)


Deseasonalizer = Deseasonaliser


class ConditionalDeseasonaliser(Deseasonaliser):
    """A transformer that removes a seasonal and trend components from time series, conditional on seasonality test.

    Parameters
    ----------
    seasonality_test : callable, optional (default=None)
        Callable that tests for seasonality and returns True when data is seasonal and False otherwise. If None,
        90% autocorrelation seasonality test is used.
    sp : int, optional (default=1)
        Seasonal periodicity
    model : str {"additive", "multiplicative"}, optional (default="additive")
        Model to use for estimating seasonal component
    """

    def __init__(self, seasonality_test=None, sp=1, model="additive"):
        self.seasonality_test = seasonality_test
        self.is_seasonal_ = None
        super(ConditionalDeseasonaliser, self).__init__(sp=sp, model=model)

    def _check_condition(self, y):
        """Check if y meets condition"""

        if not callable(self.seasonality_test):
            raise ValueError(f"`func` must be a function/callable, but found: {type(self.seasonality_test)}")

        is_seasonal = self.seasonality_test(y, sp=self.sp)
        if not isinstance(is_seasonal, (bool, np.bool_)):
            raise ValueError(f"Return type of `func` must be boolean, "
                             f"but found: {type(is_seasonal)}")
        return is_seasonal

    def fit(self, y, **fit_params):
        """Fit.

        Parameters
        ----------
        y : pd.Series
        fit_params : dict

        Returns
        -------
        self
        """
        y = check_y(y)
        self._set_oh_index(y)
        sp = check_sp(self.sp)

        # set default condition
        if self.seasonality_test is None:
            self.seasonality_test = autocorrelation_seasonality_test

        # check if data meets condition
        self.is_seasonal_ = self._check_condition(y)

        if self.is_seasonal_:
            # if condition is met, apply de-seasonalisation
            self.seasonal_ = seasonal_decompose(y, model=self.model, period=sp, filt=None, two_sided=True,
                                                extrapolate_trend=0).seasonal.iloc[:sp]
        else:
            # otherwise, set idempotent seasonal components
            self.seasonal_ = np.zeros(self.sp) if self.model == "additive" else np.ones(self.sp)

        self._is_fitted = True
        return self

    def update(self, y_new, update_params=False):
        raise NotImplementedError()


ConditionalDeseasonalizer = ConditionalDeseasonaliser
