#!/usr/bin/env python3 -u
# coding: utf-8

__author__ = ["Markus Löning"]
__all__ = ["SingleSeriesTransformAdaptor"]

import pandas as pd
from sklearn.base import clone
from sklearn.utils.metaestimators import if_delegate_has_method
from sktime.transformers.detrend._base import BaseSeriesToSeriesTransformer
from sktime.utils.validation.forecasting import check_y


class SingleSeriesTransformAdaptor(BaseSeriesToSeriesTransformer):
    """Adaptor for scikit-learn-like tabular transformers to single series setting

    Parameters
    ----------
    transformer : Estimator
        Transformer to fit and apply to single series
    """

    _required_parameters = ["transformer"]

    def __init__(self, transformer):
        self.transformer = transformer
        self.transformer_ = None
        super(SingleSeriesTransformAdaptor, self).__init__()

    def fit(self, y_train, **fit_params):
        """Fit.

        Parameters
        ----------
        y_train : pd.Series
        fit_params : dict

        Returns
        -------
        self
        """
        check_y(y_train)

        x_train = self._tabularise(y_train)
        transformer = clone(self.transformer)
        self.transformer_ = transformer.fit(x_train)
        self._is_fitted = True
        return self

    @staticmethod
    def _tabularise(y):
        """Helper function to convert single series into single-column tabular array"""
        return y.values.reshape(-1, 1)

    @staticmethod
    def _detabularise(y, index):
        """Helper function to convert single-column tabular array to single series"""
        return pd.Series(y.ravel(), index=index)

    def transform(self, y, **transform_params):
        """Transform data.

        Parameters
        ----------
        y : pd.Series

        Returns
        -------
        yt : pd.Series
            Transformed time series.
        """
        self.check_is_fitted()
        check_y(y)

        x = self._tabularise(y)
        xt = self.transformer_.transform(x)
        return self._detabularise(xt, index=y.index)

    @if_delegate_has_method(delegate="transformer")
    def inverse_transform(self, y, **transform_params):
        """Inverse transform data.

        Parameters
        ----------
        y : pd.Series

        Returns
        -------
        yt : pd.Series
            Inverse-transformed time series.
        """
        self.check_is_fitted()
        check_y(y)

        x = self._tabularise(y)
        xt = self.transformer_.inverse_transform(x)
        return self._detabularise(xt, index=y.index)

    def update(self, y_new, update_params=False):
        raise NotImplementedError("update is not implemented yet")
