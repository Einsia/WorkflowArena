# Target interface (signatures + docstrings; function bodies omitted)

The following public interfaces must be provided. Names marked "internal interface used directly by the tests" are also imported/called directly by the hidden tests and must be provided with the same name and signature.

## `statsmodels.discrete.truncated_model`  (file `statsmodels/discrete/truncated_model.py`)

```python
__all__ = ['HurdleCountModel', 'TruncatedLFNegativeBinomialP', 'TruncatedLFPoisson']

# [internal interface used directly by the tests]
class TruncatedLFGeneric(CountModel):

    def __init__(self, endog, exog, truncation=0, offset=None,
                     exposure=None, missing='none', **kwargs):
        ...

    def loglike(self, params):
        r"""Loglikelihood of Generic Truncated model

        Parameters
        ----------
        params : array-like
            The parameters of the model.

        Returns
        -------
        loglike : float
            The log-likelihood function of the model evaluated at `params`.
            See notes.

        Notes
        -----
        """
        ...

    def loglikeobs(self, params):
        r"""Loglikelihood for observations of Generic Truncated model

        Parameters
        ----------
        params : array-like
            The parameters of the model.

        Returns
        -------
        loglike : ndarray (nobs,)
            The log likelihood for each observation of the model evaluated
            at `params`. See Notes

        Notes
        -----
        """
        ...

    def score_obs(self, params):
        r"""Generic Truncated model score (gradient) vector of the log-likelihood

        Parameters
        ----------
        params : array-like
            The parameters of the model

        Returns
        -------
        score : ndarray, 1-D
            The score vector of the model, i.e. the first derivative of the
            loglikelihood function, evaluated at `params`
        """
        ...

    def score(self, params):
        r"""Generic Truncated model score (gradient) vector of the log-likelihood

        Parameters
        ----------
        params : array-like
            The parameters of the model

        Returns
        -------
        score : ndarray, 1-D
            The score vector of the model, i.e. the first derivative of the
            loglikelihood function, evaluated at `params`
        """
        ...

    def fit(self, start_params=None, method='bfgs', maxiter=35,
                full_output=1, disp=1, callback=None,
                cov_type='nonrobust', cov_kwds=None, use_t=None, **kwargs):
        ...

    def fit_regularized(
                self, start_params=None, method='l1',
                maxiter='defined_by_method', full_output=1, disp=1, callback=None,
                alpha=0, trim_mode='auto', auto_trim_tol=0.01, size_trim_tol=1e-4,
                qc_tol=0.03, **kwargs):
        ...

    def hessian(self, params):
        r"""Generic Truncated model Hessian matrix of the loglikelihood

        Parameters
        ----------
        params : array-like
            The parameters of the model

        Returns
        -------
        hess : ndarray, (k_vars, k_vars)
            The Hessian, second derivative of loglikelihood function,
            evaluated at `params`

        Notes
        -----
        """
        ...

    def predict(self, params, exog=None, exposure=None, offset=None,
                    which='mean', y_values=None):
        r"""Paramaters
        ----------
        y_values : array-like or int
            The counts for which you want the probabilities. If y_values is
            None then the probabilities for each count from 0 to max(y) are
            given.

        Predict response variable of a count model given exogenous variables.
        Notes
        -----
        If exposure is specified, then it will be logged by the method.
        The user does not need to log it first.
        """
        ...

class TruncatedLFPoisson(TruncatedLFGeneric):

    def __init__(self, endog, exog, offset=None, exposure=None,
                     truncation=0, missing='none', **kwargs):
        ...

class TruncatedLFNegativeBinomialP(TruncatedLFGeneric):

    def __init__(self, endog, exog, offset=None, exposure=None,
                     truncation=0, p=2, missing='none', **kwargs):
        ...

# [internal interface used directly by the tests]
class TruncatedLFGeneralizedPoisson(TruncatedLFGeneric):

    def __init__(self, endog, exog, offset=None, exposure=None,
                     truncation=0, p=2, missing='none', **kwargs):
        ...

class HurdleCountModel(CountModel):

    def __init__(self, endog, exog, offset=None,
                     dist="poisson", zerodist="poisson",
                     p=2, pzero=2,
                     exposure=None, missing='none', **kwargs):
        ...

    def loglike(self, params):
        r"""Loglikelihood of Generic Hurdle model

        Parameters
        ----------
        params : array-like
            The parameters of the model.

        Returns
        -------
        loglike : float
            The log-likelihood function of the model evaluated at `params`.
            See notes.

        Notes
        -----
        """
        ...

    def fit(self, start_params=None, method='bfgs', maxiter=35,
                full_output=1, disp=1, callback=None,
                cov_type='nonrobust', cov_kwds=None, use_t=None, **kwargs):
        ...

    def predict(self, params, exog=None, exposure=None,
                    offset=None, which='mean', y_values=None):
        r"""Predict response variable or other statistic given exogenous variables.

        Parameters
        ----------
        params : array_like
            The parameters of the model.
        exog : ndarray, optional
            Explanatory variables for the main count model.
            If ``exog`` is None, then the data from the model will be used.
        exog_infl : ndarray, optional
            Explanatory variables for the zero-inflation model.
            ``exog_infl`` has to be provided if ``exog`` was provided unless
            ``exog_infl`` in the model is only a constant.
        offset : ndarray, optional
            Offset is added to the linear predictor of the mean function with
            coefficient equal to 1.
            Default is zero if exog is not None, and the model offset if exog
            is None.
        exposure : ndarray, optional
            Log(exposure) is added to the linear predictor with coefficient
            equal to 1. If exposure is specified, then it will be logged by
            the method. The user does not need to log it first.
            Default is one if exog is is not None, and it is the model exposure
            if exog is None.
        which : str (optional)
            Statitistic to predict. Default is 'mean'.

            - 'mean' : the conditional expectation of endog E(y | x)
            - 'mean-main' : mean parameter of truncated count model.
              Note, this is not the mean of the truncated distribution.
            - 'linear' : the linear predictor of the truncated count model.
            - 'var' : returns the estimated variance of endog implied by the
              model.
            - 'prob-main' : probability of selecting the main model which is
                the probability of observing a nonzero count P(y > 0 | x).
            - 'prob-zero' : probability of observing a zero count. P(y=0 | x).
              This is equal to is ``1 - prob-main``
            - 'prob-trunc' : probability of truncation of the truncated count
              model. This is the probability of observing a zero count implied
              by the truncation model.
            - 'mean-nonzero' : expected value conditional on having observation
              larger than zero, E(y | X, y>0)
            - 'prob' : probabilities of each count from 0 to max(endog), or
              for y_values if those are provided. This is a multivariate
              return (2-dim when predicting for several observations).

        y_values : array_like
            Values of the random variable endog at which pmf is evaluated.
            Only used if ``which="prob"``

        Return
        ------
        predicted values

        Notes
        -----
        'prob-zero' / 'prob-trunc' is the ratio of probabilities of observing
        a zero count between hurdle model and the truncated count model.
        If this ratio is larger than one, then the hurdle model has an inflated
        number of zeros compared to the count model. If it is smaller than one,
        then the number of zeros is deflated.
        """
        ...

# [internal interface used directly by the tests]
class TruncatedLFGenericResults(CountResults):
    ...

# [internal interface used directly by the tests]
class TruncatedLFPoissonResults(TruncatedLFGenericResults):
    ...

# [internal interface used directly by the tests]
class TruncatedNegativeBinomialResults(TruncatedLFGenericResults):
    ...

# [internal interface used directly by the tests]
class L1TruncatedLFGenericResults(L1CountResults, TruncatedLFGenericResults):
    ...

# [internal interface used directly by the tests]
class TruncatedLFGenericResultsWrapper(lm.RegressionResultsWrapper):
    ...

# [internal interface used directly by the tests]
class L1TruncatedLFGenericResultsWrapper(lm.RegressionResultsWrapper):
    ...

# [internal interface used directly by the tests]
class HurdleCountResults(CountResults):

    def __init__(self, model, mlefit, results_zero, results_count,
                     cov_type='nonrobust', cov_kwds=None, use_t=None):
        ...

    @cache_readonly
    def llnull(self):
        ...

    @cache_readonly
    def bse(self):
        ...

# [internal interface used directly by the tests]
class L1HurdleCountResults(L1CountResults, HurdleCountResults):
    ...

# [internal interface used directly by the tests]
class HurdleCountResultsWrapper(lm.RegressionResultsWrapper):
    ...

# [internal interface used directly by the tests]
class L1HurdleCountResultsWrapper(lm.RegressionResultsWrapper):
    ...

```

## `statsmodels.distributions.discrete`  (file `statsmodels/distributions/discrete.py`)

```python
# [name used directly by the tests]
truncatedpoisson = truncatedpoisson_gen(name='truncatedpoisson',
                                        longname='Truncated Poisson')

# [name used directly by the tests]
truncatednegbin = truncatednegbin_gen(name='truncatednegbin',
    longname='Truncated Generalized Negative Binomial')

```
