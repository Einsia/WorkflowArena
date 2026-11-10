# Target interface (signatures + docstrings; function bodies omitted)

The following public interfaces must be provided. Names marked "internal interface used directly by the tests" are also imported/called directly by the hidden tests and must be provided with the same name and signature.

## `statsmodels.tsa.exponential_smoothing.base`  (file `statsmodels/tsa/exponential_smoothing/base.py`)

```python
class StateSpaceMLEModel(tsbase.TimeSeriesModel):
    r"""This is a temporary base model from ETS, here I just copy everything I need
    from statespace.mlemodel.MLEModel
    """

    def __init__(
            self, endog, exog=None, dates=None, freq=None, missing="none", **kwargs
        ):
        ...

    @staticmethod
    def prepare_data(data):
        ...

    def clone(self, endog, exog=None, **kwargs):
        ...

    @property
    def k_params(self):
        ...

    @contextlib.contextmanager
    def fix_params(self, params):
        r"""Fix parameters to specific values (context manager)

        Parameters
        ----------
        params : dict
            Dictionary describing the fixed parameter values, of the form
            `param_name: fixed_value`. See the `param_names` property for valid
            parameter names.

        Examples
        --------
        >>> mod = sm.tsa.SARIMAX(endog, order=(1, 0, 1))
        >>> with mod.fix_params({'ar.L1': 0.5}):
                res = mod.fit()
        """
        ...

    def fit_constrained(self, constraints, start_params=None, **fit_kwds):
        r"""Fit the model with some parameters subject to equality constraints.

        Parameters
        ----------
        constraints : dict
            Dictionary of constraints, of the form `param_name: fixed_value`.
            See the `param_names` property for valid parameter names.
        start_params : array_like, optional
            Initial guess of the solution for the loglikelihood maximization.
            If None, the default is given by Model.start_params.
        **fit_kwds : keyword arguments
            fit_kwds are used in the optimization of the remaining parameters.

        Returns
        -------
        results : Results instance

        Examples
        --------
        >>> mod = sm.tsa.SARIMAX(endog, order=(1, 0, 1))
        >>> res = mod.fit_constrained({'ar.L1': 0.5})
        """
        ...

    @property
    def start_params(self):
        r"""(array) Starting parameters for maximum likelihood estimation.
        """
        ...

    @property
    def param_names(self):
        r"""(list of str) List of human readable parameter names (for parameters
        actually included in the model).
        """
        ...

    @classmethod
    def from_formula(
            cls, formula, data, subset=None, drop_cols=None, *args, **kwargs
        ):
        r"""Not implemented for state space models
        """
        ...

class StateSpaceMLEResults(tsbase.TimeSeriesModelResults):
    r"""Class to hold results from fitting a state space model.

    Parameters
    ----------
    model : MLEModel instance
        The fitted model instance
    params : ndarray
        Fitted parameters

    Attributes
    ----------
    model : Model instance
        A reference to the model that was fit.
    nobs : float
        The number of observations used to fit the model.
    params : ndarray
        The parameters of the model.
    """

    def __init__(self, model, params, scale=1.0):
        ...

    @cache_readonly
    def nobs_effective(self):
        ...

    @cache_readonly
    def df_model(self):
        ...

    @cache_readonly
    def df_resid(self):
        ...

    @cache_readonly
    def aic(self):
        r"""(float) Akaike Information Criterion
        """
        ...

    @cache_readonly
    def aicc(self):
        r"""(float) Akaike Information Criterion with small sample correction
        """
        ...

    @cache_readonly
    def bic(self):
        r"""(float) Bayes Information Criterion
        """
        ...

    @cache_readonly
    def fittedvalues(self):
        ...

    @cache_readonly
    def hqic(self):
        r"""(float) Hannan-Quinn Information Criterion
        """
        ...

    @cache_readonly
    def llf(self):
        r"""(float) The value of the log-likelihood function evaluated at `params`.
        """
        ...

    @cache_readonly
    def mae(self):
        r"""(float) Mean absolute error
        """
        ...

    @cache_readonly
    def mse(self):
        r"""(float) Mean squared error
        """
        ...

    @cache_readonly
    def pvalues(self):
        r"""(array) The p-values associated with the z-statistics of the
        coefficients. Note that the coefficients are assumed to have a Normal
        distribution.
        """
        ...

    @cache_readonly
    def resid(self):
        ...

    @cache_readonly
    def sse(self):
        r"""(float) Sum of squared errors
        """
        ...

    @cache_readonly
    def zvalues(self):
        r"""(array) The z-statistics for the coefficients.
        """
        ...

    @cache_readonly
    def cov_params_approx(self):
        r"""(array) The variance / covariance matrix. Computed using the numerical
        Hessian approximated by complex step or finite differences methods.
        """
        ...

    def summary(
            self,
            alpha=0.05,
            start=None,
            title=None,
            model_name=None,
            display_params=True,
        ):
        r"""Summarize the Model

        Parameters
        ----------
        alpha : float, optional
            Significance level for the confidence intervals. Default is 0.05.
        start : int, optional
            Integer of the start observation. Default is 0.
        model_name : str
            The name of the model used. Default is to use model class name.

        Returns
        -------
        summary : Summary instance
            This holds the summary table and text, which can be printed or
            converted to various output formats.

        See Also
        --------
        statsmodels.iolib.summary.Summary
        """
        ...

```

## `statsmodels.tsa.exponential_smoothing.ets`  (file `statsmodels/tsa/exponential_smoothing/ets.py`)

```python
class ETSModel(base.StateSpaceMLEModel):
    r"""ETS models.

    Parameters
    ----------
    endog : array_like
        The observed time-series process :math:`y`
    error: str, optional
        The error model. "add" (default) or "mul".
    trend : str or None, optional
        The trend component model. "add", "mul", or None (default).
    damped_trend : bool, optional
        Whether or not an included trend component is damped. Default is False.
    seasonal : str, optional
        The seasonality model. "add", "mul", or None (default).
    seasonal_periods: int, optional
        The number of periods in a complete seasonal cycle for seasonal
        (Holt-Winters) models. For example, 4 for quarterly data with an
        annual cycle or 7 for daily data with a weekly cycle. Required if
        `seasonal` is not None.
    initialization_method : str, optional
        Method for initialization of the state space model. One of:

        * 'estimated' (default)
        * 'heuristic'
        * 'known'

        If 'known' initialization is used, then `initial_level` must be
        passed, as well as `initial_trend` and `initial_seasonal` if
        applicable.
        'heuristic' uses a heuristic based on the data to estimate initial
        level, trend, and seasonal state. 'estimated' uses the same heuristic
        as initial guesses, but then estimates the initial states as part of
        the fitting process.  Default is 'estimated'.
    initial_level : float, optional
        The initial level component. Only used if initialization is 'known'.
    initial_trend : float, optional
        The initial trend component. Only used if initialization is 'known'.
    initial_seasonal : array_like, optional
        The initial seasonal component. An array of length `seasonal`.  Only
        used if initialization is 'known'.
    bounds : dict or None, optional
        A dictionary with parameter names as keys and the respective bounds
        intervals as values (lists/tuples/arrays).
        The availabe parameter names are, depeding on the model and
        initialization method:
            * "smoothing_level"
            * "smoothing_trend"
            * "smoothing_seasonal"
            * "damping_trend"
            * "initial_level"
            * "initial_trend"
            * "initial_seasonal.0", ..., "initial_seasonal.<m-1>"
        The default option is ``None``, in which case the traditional
        (nonlinear) bounds as described in [1]_ are used.
    """

    def __init__(
            self,
            endog,
            error="add",
            trend=None,
            damped_trend=False,
            seasonal=None,
            seasonal_periods=None,
            initialization_method="estimated",
            initial_level=None,
            initial_trend=None,
            initial_seasonal=None,
            bounds=None,
            dates=None,
            freq=None,
            missing="none",
        ):
        ...

    def set_initialization_method(
            self,
            initialization_method,
            initial_level=None,
            initial_trend=None,
            initial_seasonal=None,
        ):
        r"""Sets a new initialization method for the state space model.

        Parameters
        ----------
        initialization_method : str, optional
            Method for initialization of the state space model. One of:

            * 'estimated' (default)
            * 'heuristic'
            * 'known'

            If 'known' initialization is used, then `initial_level` must be
            passed, as well as `initial_trend` and `initial_seasonal` if
            applicable.
            'heuristic' uses a heuristic based on the data to estimate initial
            level, trend, and seasonal state. 'estimated' uses the same
            heuristic as initial guesses, but then estimates the initial states
            as part of the fitting process. Default is 'estimated'.
        initial_level : float, optional
            The initial level component. Only used if initialization is
            'known'.
        initial_trend : float, optional
            The initial trend component. Only used if initialization is
            'known'.
        initial_seasonal : array_like, optional
            The initial seasonal component. An array of length `seasonal`. Only
            used if initialization is 'known'.
        """
        ...

    def set_bounds(self, bounds):
        r"""Set bounds for parameter estimation.

        Parameters
        ----------
        bounds : dict or None, optional
            A dictionary with parameter names as keys and the respective bounds
            intervals as values (lists/tuples/arrays).
            The available parameter names are in ``self.param_names``.
            The default option is ``None``, in which case the traditional
            (nonlinear) bounds as described in [1]_ are used.
        """
        ...

    @staticmethod
    def prepare_data(data):
        r"""Prepare data for use in the state space representation
        """
        ...

    @property
    def nobs_effective(self):
        ...

    @property
    def short_name(self):
        ...

    @property
    def state_names(self):
        ...

    @property
    def initial_state_names(self):
        ...

    @property
    def k_params(self):
        ...

    def fit(
            self,
            start_params=None,
            maxiter=1000,
            full_output=True,
            disp=True,
            callback=None,
            return_params=False,
            **kwargs,
        ):
        r"""Fit an ETS model by maximizing log-likelihood.

        Log-likelihood is a function of the model parameters :math:`\alpha,
        \beta, \gamma, \phi` (depending on the chosen model), and, if
        `initialization_method` was set to `'estimated'` in the constructor,
        also the initial states :math:`l_{-1}, b_{-1}, s_{-1}, \ldots, s_{-m}`.

        The fit is performed using the L-BFGS algorithm.

        Parameters
        ----------
        start_params : array_like, optional
            Initial values for parameters that will be optimized. If this is
            ``None``, default values will be used.
            The length of this depends on the chosen model. This should contain
            the parameters in the following order, skipping parameters that do
            not exist in the chosen model.

            * `smoothing_level` (:math:`\alpha`)
            * `smoothing_trend` (:math:`\beta`)
            * `smoothing_seasonal` (:math:`\gamma`)
            * `damping_trend` (:math:`\phi`)

            If ``initialization_method`` was set to ``'estimated'`` (the
            default), additionally, the parameters

            * `initial_level` (:math:`l_{-1}`)
            * `initial_trend` (:math:`l_{-1}`)
            * `initial_seasonal.0` (:math:`s_{-1}`)
            * ...
            * `initial_seasonal.<m-1>` (:math:`s_{-m}`)

            also have to be specified.
        maxiter : int, optional
            The maximum number of iterations to perform.
        full_output : bool, optional
            Set to True to have all available output in the Results object's
            mle_retvals attribute. The output is dependent on the solver.
            See LikelihoodModelResults notes section for more information.
        disp : bool, optional
            Set to True to print convergence messages.
        callback : callable callback(xk), optional
            Called after each iteration, as callback(xk), where xk is the
            current parameter vector.
        return_params : bool, optional
            Whether or not to return only the array of maximizing parameters.
            Default is False.
        **kwargs
            Additional keyword arguments to pass to the optimizer.

        Returns
        -------
        results : ETSResults
        """
        ...

    @contextlib.contextmanager
    def use_internal_loglike(self):
        ...

    def loglike(self, params, **kwargs):
        r"""Log-likelihood of model.

        Parameters
        ----------
        params : np.ndarray of np.float
            Model parameters: (alpha, beta, gamma, phi, l[-1],
            b[-1], s[-1], ..., s[-m])

        Notes
        -----
        The log-likelihood of a exponential smoothing model is [1]_:

        .. math::

           l(\theta, x_0|y) = - \frac{n}{2}(\log(2\pi s^2) + 1)
                              - \sum\limits_{t=1}^n \log(k_t)

        with

        .. math::

           s^2 = \frac{1}{n}\sum\limits_{t=1}^n \frac{\hat{y}_t - y_t}{k_t}

        where :math:`k_t = 1` for the additive error model and :math:`k_t =
        y_t` for the multiplicative error model.

        References
        ----------
        .. [1] J. K. Ord, A. B. Koehler R. D. and Snyder (1997). Estimation and
           Prediction for a Class of Dynamic Nonlinear Statistical Models.
           *Journal of the American Statistical Association*, 92(440),
           1621-1629
        """
        ...

    def smooth(self, params, return_raw=False):
        r"""Exponential smoothing with given parameters

        Parameters
        ----------
        params : array_like
            Model parameters
        return_raw : bool, optional
            Whether to return only the state space results or the full results
            object. Default is ``False``.

        Returns
        -------
        result : ETSResultsWrapper or tuple
            If ``return_raw=False``, returns a ETSResultsWrapper
            object. Otherwise a tuple of arrays or pandas objects, depending on
            the format of the endog data.
        """
        ...

    def hessian(
            self, params, approx_centered=False, approx_complex_step=True, **kwargs
        ):
        r"""Hessian matrix of the likelihood function, evaluated at the given
        parameters

        Parameters
        ----------
        params : array_like
            Array of parameters at which to evaluate the hessian.
        approx_centered : bool
            Whether to use a centered scheme for finite difference
            approximation
        approx_complex_step : bool
            Whether to use complex step differentiation for approximation

        Returns
        -------
        hessian : ndarray
            Hessian matrix evaluated at `params`

        Notes
        -----
        This is a numerical approximation.
        """
        ...

    def score(
            self, params, approx_centered=False, approx_complex_step=True, **kwargs
        ):
        ...

    def update(params, *args, **kwargs):
        ...

class ETSResults(base.StateSpaceMLEResults):

    def __init__(self, model, params, results):
        ...

    @cache_readonly
    def nobs_effective(self):
        ...

    @cache_readonly
    def df_model(self):
        ...

    @cache_readonly
    def fittedvalues(self):
        ...

    @cache_readonly
    def resid(self):
        ...

    @cache_readonly
    def llf(self):
        r"""log-likelihood function evaluated at the fitted params
        """
        ...

    def simulate(
            self,
            nsimulations,
            anchor=None,
            repetitions=1,
            random_errors=None,
            random_state=None,
        ):
        r"""Random simulations using the state space formulation.

        Parameters
        ----------
        nsimulations : int
            The number of simulation steps.
        anchor : int, str, or datetime, optional
            First period for simulation. The simulation will be conditional on
            all existing datapoints prior to the `anchor`.  Type depends on the
            index of the given `endog` in the model. Two special cases are the
            strings 'start' and 'end'. `start` refers to beginning the
            simulation at the first period of the sample, and `end` refers to
            beginning the simulation at the first period after the sample.
            Integer values can run from 0 to `nobs`, or can be negative to
            apply negative indexing. Finally, if a date/time index was provided
            to the model, then this argument can be a date string to parse or a
            datetime type. Default is 'start'.
        repetitions : int, optional
            Number of simulated paths to generate. Default is 1 simulated path.
        random_errors : optional
            Specifies how the random errors should be obtained. Can be one of
            the following:

            * ``None``: Random normally distributed values with variance
              estimated from the fit errors drawn from numpy's standard
              RNG (can be seeded with the `random_state` argument). This is the
              default option.
            * A distribution function from ``scipy.stats``, e.g.
              ``scipy.stats.norm``: Fits the distribution function to the fit
              errors and draws from the fitted distribution.
              Note the difference between ``scipy.stats.norm`` and
              ``scipy.stats.norm()``, the latter one is a frozen distribution
              function.
            * A frozen distribution function from ``scipy.stats``, e.g.
              ``scipy.stats.norm(scale=2)``: Draws from the frozen distribution
              function.
            * A ``np.ndarray`` with shape (`nsimulations`, `repetitions`): Uses
              the given values as random errors.
            * ``"bootstrap"``: Samples the random errors from the fit errors.

        random_state : int or np.random.RandomState, optional
            A seed for the random number generator or a
            ``np.random.RandomState`` object. Only used if `random_errors` is
            ``None``. Default is ``None``.

        Returns
        -------
        sim : pd.Series, pd.DataFrame or np.ndarray
            An ``np.ndarray``, ``pd.Series``, or ``pd.DataFrame`` of simulated
            values.
            If the original data was a ``pd.Series`` or ``pd.DataFrame``, `sim`
            will be a ``pd.Series`` if `repetitions` is 1, and a
            ``pd.DataFrame`` of shape (`nsimulations`, `repetitions`) else.
            Otherwise, if `repetitions` is 1, a ``np.ndarray`` of shape
            (`nsimulations`,) is returned, and if `repetitions` is not 1 a
            ``np.ndarray`` of shape (`nsimulations`, `repetitions`) is
            returned.
        """
        ...

    def forecast(self, steps=1):
        r"""Out-of-sample forecasts

        Parameters
        ----------
        steps : int, str, or datetime, optional
            If an integer, the number of steps to forecast from the end of the
            sample. Can also be a date string to parse or a datetime type.
            However, if the dates index does not have a fixed frequency, steps
            must be an integer. Default

        Returns
        -------
        forecast : ndarray
            Array of out of sample forecasts. A (steps x k_endog) array.
        """
        ...

    def predict(self, start=None, end=None, dynamic=False, index=None):
        r"""In-sample prediction and out-of-sample forecasting

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
            want out of sample prediction. Default is the last observation in
            the sample.
        dynamic : bool, int, str, or datetime, optional
            Integer offset relative to `start` at which to begin dynamic
            prediction. Can also be an absolute date string to parse or a
            datetime type (these are not interpreted as offsets).
            Prior to this observation, true endogenous values will be used for
            prediction; starting with this observation and continuing through
            the end of prediction, forecasted endogenous values will be used
            instead.
        index : pd.Index, optional
            Optionally an index to associate the predicted results to. If None,
            an attempt is made to create an index for the predicted results
            from the model's index or model's row labels.

        Returns
        -------
        forecast : array_like or pd.Series.
            Array of out of in-sample predictions and / or out-of-sample
            forecasts. An (npredict,) array. If original data was a pd.Series
            or DataFrame, a pd.Series is returned.
        """
        ...

    def summary(self, alpha=0.05, start=None):
        r"""Summarize the fitted model

        Parameters
        ----------
        alpha : float, optional
            Significance level for the confidence intervals. Default is 0.05.
        start : int, optional
            Integer of the start observation. Default is 0.

        Returns
        -------
        summary : Summary instance
            This holds the summary table and text, which can be printed or
            converted to various output formats.

        See Also
        --------
        statsmodels.iolib.summary.Summary
        """
        ...

class ETSResultsWrapper(wrap.ResultsWrapper):
    ...

```
