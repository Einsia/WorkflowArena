# Target interface (signatures + docstrings; function bodies omitted)

The following public interfaces must be provided. Names marked "internal interface used directly by the tests" are also imported/called directly by the hidden tests and must be provided with the same name and signature.

## `statsmodels.tsa.ardl`  (file `statsmodels/tsa/ardl.py`)

```python
__all__ = ['ARDL', 'ARDLOrderSelectionResults', 'ARDLResults', 'ardl_select_order']

class ARDL(AutoReg):
    r"""Autoregressive Distributed Lag (ARDL) Model

    Parameters
    ----------
    endog : array_like
        A 1-d endogenous response variable. The dependent variable.
    lags : {int, list[int]}
        The number of lags to include in the model if an integer or the
        list of lag indices to include.  For example, [1, 4] will only
        include lags 1 and 4 while lags=4 will include lags 1, 2, 3, and 4.
    exog : array_like
        Exogenous variables to include in the model. Either a DataFrame or
        an 2-d array-like structure that can be converted to a NumPy array.
    order : {int, sequence[int], dict}
        If int, uses lags 0, 1, ..., order  for all exog variables. If
        sequence[int], uses the ``order`` for all variables. If a dict,
        applies the lags series by series. If ``exog`` is anything other
        than a DataFrame, the keys are the column index of exog (e.g., 0,
        1, ...). If a DataFrame, keys are column names.
    fixed : array_like
        Additional fixed regressors that are not lagged.
    causal : bool, optional
        Whether to include lag 0 of exog variables.  If True, only includes
        lags 1, 2, ...
    trend : {'n', 'c', 't', 'ct'}, optional
        The trend to include in the model:

        * 'n' - No trend.
        * 'c' - Constant only.
        * 't' - Time trend only.
        * 'ct' - Constant and time trend.

        The default is 'c'.

    seasonal : bool, optional
        Flag indicating whether to include seasonal dummies in the model. If
        seasonal is True and trend includes 'c', then the first period
        is excluded from the seasonal terms.
    deterministic : DeterministicProcess, optional
        A deterministic process.  If provided, trend and seasonal are ignored.
        A warning is raised if trend is not "n" and seasonal is not False.
    hold_back : {None, int}, optional
        Initial observations to exclude from the estimation sample.  If None,
        then hold_back is equal to the maximum lag in the model.  Set to a
        non-zero value to produce comparable models with different lag
        length.  For example, to compare the fit of a model with lags=3 and
        lags=1, set hold_back=3 which ensures that both models are estimated
        using observations 3,...,nobs. hold_back must be >= the maximum lag in
        the model.
    period : {None, int}, optional
        The period of the data. Only used if seasonal is True. This parameter
        can be omitted if using a pandas object for endog that contains a
        recognized frequency.
    missing : {"none", "drop", "raise"}, optional
        Available options are 'none', 'drop', and 'raise'. If 'none', no nan
        checking is done. If 'drop', any observations with nans are dropped.
        If 'raise', an error is raised. Default is 'none'.

    Notes
    -----
    The full specification of an ARDL is

    .. math ::

       Y_t = \delta_0 + \delta_1 t + \delta_2 t^2
             + \sum_{i=1}^{s-1} \gamma_i I_{[(\mod(t,s) + 1) = i]}
             + \sum_{j=1}^p \phi_j Y_{t-j}
             + \sum_{l=1}^k \sum_{m=0}^{o_l} \beta_{l,m} X_{l, t-m}
             + Z_t \lambda
             + \epsilon_t

    where :math:`\delta_\bullet` capture trends, :math:`\gamma_\bullet`
    capture seasonal shifts, s is the period of the seasonality, p is the
    lag length of the endogenous variable, k is the number of exogenous
    variables :math:`X_{l}`, :math:`o_l` is included the lag length of
    :math:`X_{l}`, :math:`Z_t` are ``r`` included fixed regressors and
    :math:`\epsilon_t` is a white noise shock. If ``causal`` is ``True``,
    then the 0-th lag of the exogenous variables is not included and the
    sum starts at ``m=1``.

    See Also
    --------
    statsmodels.tsa.ar_model.AutoReg
        Autoregressive model estimation with optional exogenous regressors
    statsmodels.tsa.statespace.sarimax.SARIMAX
        Seasonal ARIMA model estimation with optional exogenous regressors
    statsmodels.tsa.arima.model.ARIMA
        ARIMA model estimation

    Examples
    --------
    >>> from statsmodels.tsa.api import ARDL
    >>> from statsmodels.datasets import danish_data
    >>> data = danish_data.load_pandas().data
    >>> lrm = data.lrm
    >>> exog = data[["lry", "ibo", "ide"]]

    A biasic model where all variables have 3 lags included

    >>> ARDL(data.lrm, 3, data[["lry", "ibo", "ide"]], 3)

    A dictionary can be used to pass custom lag orders

    >>> ARDL(data.lrm, [1, 3], exog, {"lry": 1, "ibo": 3, "ide": 2})

    Setting causal removes the 0-th lag from the exogenous variables

    >>> exog_lags = {"lry": 1, "ibo": 3, "ide": 2}
    >>> ARDL(data.lrm, [1, 3], exog, exog_lags, causal=True)

    A dictionary can also be used to pass specific lags to include.
    Sequences hold the specific lags to include, while integers are expanded
    to include [0, 1, ..., lag]. If causal is False, then the 0-th lag is
    excluded.

    >>> ARDL(lrm, [1, 3], exog, {"lry": [0, 1], "ibo": [0, 1, 3], "ide": 2})

    When using NumPy arrays, the dictionary keys are the column index.

    >>> import numpy as np
    >>> lrma = np.asarray(lrm)
    >>> exoga = np.asarray(exog)
    >>> ARDL(lrma, 3, exoga, {0: [0, 1], 1: [0, 1, 3], 2: 2})
    """

    def __init__(
            self,
            endog: Union[Sequence[float], pd.Series, _ArrayLike2D],
            lags: Union[None, int, Sequence[int]],
            exog: Optional[_ArrayLike2D] = None,
            order: _ARDLOrder = 0,
            trend: Literal["n", "c", "ct", "ctt"] = "c",
            *,
            fixed: Optional[_ArrayLike2D] = None,
            causal: bool = False,
            seasonal: bool = False,
            deterministic: Optional[DeterministicProcess] = None,
            hold_back: Optional[int] = None,
            period: Optional[int] = None,
            missing: Literal["none", "drop", "raise"] = "none",
        ) -> None:
        ...

    @property
    def ar_lags(self) -> Optional[List[int]]:
        r"""The autoregressive lags included in the model
        """
        ...

    @property
    def exog_lags(self) -> Dict[Hashable, List[int]]:
        r"""The lags of exogenous variables included in the model
        """
        ...

    @property
    def ardl_order(self) -> Tuple[int, int]:
        r"""The order of the ARDL(p,q)
        """
        ...

    def fit(
            self,
            cov_type: str = "nonrobust",
            cov_kwds: Dict[str, Any] = None,
            use_t: bool = False,
        ) -> ARDLResults:
        r"""Estimate the model parameters.

        Parameters
        ----------
        cov_type : str
            The covariance estimator to use. The most common choices are listed
            below.  Supports all covariance estimators that are available
            in ``OLS.fit``.

            * 'nonrobust' - The class OLS covariance estimator that assumes
              homoskedasticity.
            * 'HC0', 'HC1', 'HC2', 'HC3' - Variants of White's
              (or Eiker-Huber-White) covariance estimator. `HC0` is the
              standard implementation.  The other make corrections to improve
              the finite sample performance of the heteroskedasticity robust
              covariance estimator.
            * 'HAC' - Heteroskedasticity-autocorrelation robust covariance
              estimation. Supports cov_kwds.

              - `maxlags` integer (required) : number of lags to use.
              - `kernel` callable or str (optional) : kernel
                  currently available kernels are ['bartlett', 'uniform'],
                  default is Bartlett.
              - `use_correction` bool (optional) : If true, use small sample
                  correction.
        cov_kwds : dict, optional
            A dictionary of keyword arguments to pass to the covariance
            estimator. `nonrobust` and `HC#` do not support cov_kwds.
        use_t : bool, optional
            A flag indicating that inference should use the Student's t
            distribution that accounts for model degree of freedom.  If False,
            uses the normal distribution. If None, defers the choice to
            the cov_type. It also removes degree of freedom corrections from
            the covariance estimator when cov_type is 'nonrobust'.

        Returns
        -------
        ARDLResults
            Estimation results.

        See Also
        --------
        statsmodels.tsa.ar_model.AutoReg
            Ordinary Least Squares estimation.
        statsmodels.regression.linear_model.OLS
            Ordinary Least Squares estimation.
        statsmodels.regression.linear_model.RegressionResults
            See ``get_robustcov_results`` for a detailed list of available
            covariance estimators and options.

        Notes
        -----
        Use ``OLS`` to estimate model parameters and to estimate parameter
        covariance.
        """
        ...

    def predict(
            self,
            params,
            start=None,
            end=None,
            dynamic=False,
            exog=None,
            exog_oos=None,
            fixed=None,
            fixed_oos=None,
        ):
        r"""In-sample prediction and out-of-sample forecasting.

        Parameters
        ----------
        params : array_like
            The fitted model parameters.
        start : int, str, or datetime, optional
            Zero-indexed observation number at which to start forecasting,
            i.e., the first forecast is start. Can also be a date string to
            parse or a datetime type. Default is the the zeroth observation.
        end : int, str, or datetime, optional
            Zero-indexed observation number at which to end forecasting, i.e.,
            the last forecast is end. Can also be a date string to
            parse or a datetime type. However, if the dates index does not
            have a fixed frequency, end must be an integer index if you
            want out-of-sample prediction. Default is the last observation in
            the sample. Unlike standard python slices, end is inclusive so
            that all the predictions [start, start+1, ..., end-1, end] are
            returned.
        dynamic : {bool, int, str, datetime, Timestamp}, optional
            Integer offset relative to `start` at which to begin dynamic
            prediction. Prior to this observation, true endogenous values
            will be used for prediction; starting with this observation and
            continuing through the end of prediction, forecasted endogenous
            values will be used instead. Datetime-like objects are not
            interpreted as offsets. They are instead used to find the index
            location of `dynamic` which is then used to to compute the offset.
        exog : array_like
            A replacement exogenous array.  Must have the same shape as the
            exogenous data array used when the model was created.
        exog_oos : array_like
            An array containing out-of-sample values of the exogenous
            variables. Must have the same number of columns as the exog
            used when the model was created, and at least as many rows as
            the number of out-of-sample forecasts.
        fixed : array_like
            A replacement fixed array.  Must have the same shape as the
            fixed data array used when the model was created.
        fixed_oos : array_like
            An array containing out-of-sample values of the fixed variables.
            Must have the same number of columns as the fixed used when the
            model was created, and at least as many rows as the number of
            out-of-sample forecasts.

        Returns
        -------
        predictions : {ndarray, Series}
            Array of out of in-sample predictions and / or out-of-sample
            forecasts.
        """
        ...

    @classmethod
    def from_formula(
            cls,
            data: pd.DataFrame,
            formula: str,
            *,
            trend: Literal["n", "c", "ct", "ctt"] = "n",
            seasonal: bool = False,
            deterministic: Optional[DeterministicProcess] = None,
            hold_back: Optional[int] = None,
            period: Optional[int] = None,
            missing: Literal["none", "raise"] = "none",
        ) -> ARDL:
        ...

class ARDLResults(AutoRegResults):
    r"""Class to hold results from fitting an ARDL model.

    Parameters
    ----------
    model : ARDL
        Reference to the model that is fit.
    params : ndarray
        The fitted parameters from the AR Model.
    cov_params : ndarray
        The estimated covariance matrix of the model parameters.
    normalized_cov_params : ndarray
        The array inv(dot(x.T,x)) where x contains the regressors in the
        model.
    scale : float, optional
        An estimate of the scale of the model.
    """

    def __init__(
            self, model, params, cov_params, normalized_cov_params=None, scale=1.0
        ):
        ...

    @Appender(remove_parameters(ARDL.predict.__doc__, "params"))
    def predict(
            self,
            start=None,
            end=None,
            dynamic=False,
            exog=None,
            exog_oos=None,
            fixed=None,
            fixed_oos=None,
        ):
        ...

    def forecast(self, steps=1, exog=None, fixed=None):
        r"""Out-of-sample forecasts

        Parameters
        ----------
        steps : {int, str, datetime}, default 1
            If an integer, the number of steps to forecast from the end of the
            sample. Can also be a date string to parse or a datetime type.
            However, if the dates index does not have a fixed frequency,
            steps must be an integer.
        exog : array_like, optional
            Exogenous values to use out-of-sample. Must have same number of
            columns as original exog data and at least `steps` rows
        fixed : array_like, optional
            Fixed values to use out-of-sample. Must have same number of
            columns as original fixed data and at least `steps` rows

        Returns
        -------
        array_like
            Array of out of in-sample predictions and / or out-of-sample
            forecasts.

        See Also
        --------
        ARDLResults.predict
            In- and out-of-sample predictions
        ARDLResults.get_prediction
            In- and out-of-sample predictions and confidence intervals
        """
        ...

    def get_prediction(
            self,
            start=None,
            end=None,
            dynamic=False,
            exog=None,
            exog_oos=None,
            fixed=None,
            fixed_oos=None,
        ):
        r"""Predictions and prediction intervals

        Parameters
        ----------
        start : int, str, or datetime, optional
            Zero-indexed observation number at which to start forecasting,
            i.e., the first forecast is start. Can also be a date string to
            parse or a datetime type. Default is the the zeroth observation.
        end : int, str, or datetime, optional
            Zero-indexed observation number at which to end forecasting, i.e.,
            the last forecast is end. Can also be a date string to
            parse or a datetime type. However, if the dates index does not
            have a fixed frequency, end must be an integer index if you
            want out-of-sample prediction. Default is the last observation in
            the sample. Unlike standard python slices, end is inclusive so
            that all the predictions [start, start+1, ..., end-1, end] are
            returned.
        dynamic : {bool, int, str, datetime, Timestamp}, optional
            Integer offset relative to `start` at which to begin dynamic
            prediction. Prior to this observation, true endogenous values
            will be used for prediction; starting with this observation and
            continuing through the end of prediction, forecasted endogenous
            values will be used instead. Datetime-like objects are not
            interpreted as offsets. They are instead used to find the index
            location of `dynamic` which is then used to to compute the offset.
        exog : array_like
            A replacement exogenous array.  Must have the same shape as the
            exogenous data array used when the model was created.
        exog_oos : array_like
            An array containing out-of-sample values of the exogenous variable.
            Must has the same number of columns as the exog used when the
            model was created, and at least as many rows as the number of
            out-of-sample forecasts.
        fixed : array_like
            A replacement fixed array.  Must have the same shape as the
            fixed data array used when the model was created.
        fixed_oos : array_like
            An array containing out-of-sample values of the fixed variables.
            Must have the same number of columns as the fixed used when the
            model was created, and at least as many rows as the number of
            out-of-sample forecasts.

        Returns
        -------
        PredictionResults
            Prediction results with mean and prediction intervals
        """
        ...

    @Substitution(predict_params=_predict_params)
    def plot_predict(
            self,
            start=None,
            end=None,
            dynamic=False,
            exog=None,
            exog_oos=None,
            fixed=None,
            fixed_oos=None,
            alpha=0.05,
            in_sample=True,
            fig=None,
            figsize=None,
        ):
        r"""        Plot in- and out-of-sample predictions

                Parameters
                ----------
        %(predict_params)s
                alpha : {float, None}
                    The tail probability not covered by the confidence interval. Must
                    be in (0, 1). Confidence interval is constructed assuming normally
                    distributed shocks. If None, figure will not show the confidence
                    interval.
                in_sample : bool
                    Flag indicating whether to include the in-sample period in the
                    plot.
                fig : Figure
                    An existing figure handle. If not provided, a new figure is
                    created.
                figsize: tuple[float, float]
                    Tuple containing the figure size values.

                Returns
                -------
                Figure
                    Figure handle containing the plot.

        """
        ...

    def summary(self, alpha=0.05):
        r"""Summarize the Model

        Parameters
        ----------
        alpha : float, optional
            Significance level for the confidence intervals.

        Returns
        -------
        smry : Summary instance
            This holds the summary table and text, which can be printed or
            converted to various output formats.

        See Also
        --------
        statsmodels.iolib.summary.Summary
        """
        ...

# [internal interface used directly by the tests]
class ARDLResultsWrapper(wrap.ResultsWrapper):
    ...

class ARDLOrderSelectionResults(AROrderSelectionResults):
    r"""Results from an ARDL order selection

    Contains the information criteria for all fitted model orders.
    """

    def __init__(self, model, ics, trend, seasonal, period):
        ...

    @property
    def exog_lags(self) -> Dict[Hashable, List[int]]:
        r"""The lags of exogenous variables in the selected model
        """
        ...

def ardl_select_order(
    endog: Union[Sequence[float], pd.Series, _ArrayLike2D],
    maxlag: int,
    exog: _ArrayLike2D,
    maxorder: Union[int, Dict[Hashable, int]],
    trend: Literal["n", "c", "ct", "ctt"] = "c",
    *,
    fixed: Optional[_ArrayLike2D] = None,
    causal: bool = False,
    ic: Literal["aic", "bic"] = "bic",
    glob: bool = False,
    seasonal: bool = False,
    deterministic: Optional[DeterministicProcess] = None,
    hold_back: Optional[int] = None,
    period: Optional[int] = None,
    missing: Literal["none", "raise"] = "none",
) -> ARDLOrderSelectionResults:
    r"""ARDL order selection

    Parameters
    ----------
    endog : array_like
        A 1-d endogenous response variable. The dependent variable.
    maxlag : int
        The maximum lag to consider for the endogenous variable.
    exog : array_like
        Exogenous variables to include in the model. Either a DataFrame or
        an 2-d array-like structure that can be converted to a NumPy array.
    maxorder : {int, dict}
        If int, sets a common max lag length for all exog variables. If
        a dict, then sets individual lag length. They keys are column names
        if exog is a DataFrame or column indices otherwise.
    trend : {'n', 'c', 't', 'ct'}, optional
        The trend to include in the model:

        * 'n' - No trend.
        * 'c' - Constant only.
        * 't' - Time trend only.
        * 'ct' - Constant and time trend.

        The default is 'c'.
    fixed : array_like
        Additional fixed regressors that are not lagged.
    causal : bool, optional
        Whether to include lag 0 of exog variables.  If True, only includes
        lags 1, 2, ...
    ic : {"aic", "bic", "hqic"}
        The information criterion to use in model selection.
    glob : bool
        Whether to consider all possible submodels of the largest model
        or only if smaller order lags must be included if larger order
        lags are.  If ``True``, the number of model considered is of the
        order 2**(maxlag + k * maxorder) assuming maxorder is an int. This
        can be very large unless k and maxorder are bot relatively small.
        If False, the number of model considered is of the order
        maxlag*maxorder**k which may also be substantial when k and maxorder
        are large.
    seasonal : bool, optional
        Flag indicating whether to include seasonal dummies in the model. If
        seasonal is True and trend includes 'c', then the first period
        is excluded from the seasonal terms.
    deterministic : DeterministicProcess, optional
        A deterministic process.  If provided, trend and seasonal are ignored.
        A warning is raised if trend is not "n" and seasonal is not False.
    hold_back : {None, int}, optional
        Initial observations to exclude from the estimation sample.  If None,
        then hold_back is equal to the maximum lag in the model.  Set to a
        non-zero value to produce comparable models with different lag
        length.  For example, to compare the fit of a model with lags=3 and
        lags=1, set hold_back=3 which ensures that both models are estimated
        using observations 3,...,nobs. hold_back must be >= the maximum lag in
        the model.
    period : {None, int}, optional
        The period of the data. Only used if seasonal is True. This parameter
        can be omitted if using a pandas object for endog that contains a
        recognized frequency.
    missing : {"none", "drop", "raise"}, optional
        Available options are 'none', 'drop', and 'raise'. If 'none', no nan
        checking is done. If 'drop', any observations with nans are dropped.
        If 'raise', an error is raised. Default is 'none'.

    Returns
    -------
    ARDLSelectionResults
        A results holder containing the selected model and the complete set
        of information criteria for all models fit.
    """
    ...

```
