> **Harbor path notes**
> - The start source snapshot is at `/work` (the "working directory `/work`" in the statement below). It has already been built and installed with the build command given below and can be imported directly.
> - The files `INTERFACE.md`, `MANIFEST.md` and `env/Dockerfile` mentioned in the statement are under `/workspace/` ("`INTERFACE.md` in the same directory" means `/workspace/INTERFACE.md`).
> - Deliverable: the `/work` directory itself. At the end, the grader collects the whole `/work` source tree, deletes compiled build products that are not part of the start tree (`*.so`, `*.o`, `build/`, `*.egg-info`, Cython-generated C/C++ files, etc.), then rebuilds it offline in a separate image and runs the hidden tests. No separate patch file is needed.
> - There is no network access at run time.

# Exponential smoothing (ETS) models in innovations state-space form

Implement the new functionality described below in the provided fixed-version `statsmodels` source snapshot (working directory `/work`, without git history).

## Background

The innovations state-space form of exponential smoothing (Hyndman et al. 2008) combines error (additive/multiplicative), trend (none/additive/damped additive) and seasonality (none/additive/multiplicative) into the ETS model family, which can be estimated by maximum likelihood and yields model-based prediction intervals. The repository's existing `statsmodels.tsa.holtwinters.ExponentialSmoothing` only does point-forecast smoothing and has no ETS likelihood framework.

## Required deliverables

1. New subpackage content: `statsmodels/tsa/exponential_smoothing/ets.py` (`ETSModel`, `ETSResults`, the prediction results object) and `statsmodels/tsa/exponential_smoothing/base.py` (reusable base classes for "state-space-style MLE model/results": parameter fixing `fix_params`, numerical derivatives, information criteria, `summary`).
2. A high-performance implementation of the smoothing recursions (Cython extension `statsmodels/tsa/exponential_smoothing/_ets_smooth.pyx`, registered in `setup.py`), covering all error/trend/seasonal combinations and damping.
3. `ETSModel(endog, error="add", trend=None, damped_trend=False, seasonal=None, seasonal_periods=None, initialization_method="estimated", initial_level=None, initial_trend=None, initial_seasonal=None, bounds=None, dates=None, freq=None, missing="none")`; `fit` supports fixing some of the parameters; initialization methods for the initial states such as estimated/heuristic/known.
4. `ETSResults`: fitted values, residuals, the state series, `forecast`, `predict`, `simulate` (random disturbances or bootstrap, multiple repetitions), `get_prediction` (analytic variance for linear models, simulated quantiles for nonlinear models), `summary`, AIC/AICc/BIC/HQIC, etc.
5. Parameter names: `smoothing_level`, `smoothing_trend`, `smoothing_seasonal`, `damping_trend`, `initial_level`, `initial_trend`, `initial_seasonal.<i>`, etc. (see the docstrings in INTERFACE).

The complete target interface (signatures + docstring-level descriptions) is in `INTERFACE.md` in the same directory. Function bodies are omitted; the behavior described by the docstrings is the acceptance criterion. Names marked "internal interface used directly by the tests" must also be provided with the same name and the same signature.

## Allowed scope of changes

- You may add modules and Cython extensions under `statsmodels/tsa/exponential_smoothing/` and modify `setup.py` to register the extension.
- Every other file of the start tree is hash-protected, including test helpers (e.g. `_testutils` modules), `conftest.py` files, build scripts and packaging configuration not listed above: modifying or deleting any of them, or replacing it with a symlink, scores 0. New files may be added, except files named `conftest.py`, `pytest.ini`, `tox.ini`, `setup.cfg`, `pyproject.toml`, `sitecustomize.py`, `usercustomize.py` or `*.pth`, and except symlinks.
- Do not modify existing tests or build dependencies; do not access the network.

## Environment and commands

- Environment: the image described by `env/Dockerfile` (dependency versions pinned to the repository's ecosystem at that time); working directory `/work`; no network during evaluation.
- Build: `cd /work && SETUPTOOLS_SCM_PRETEND_VERSION=0.13.0.dev0 python setup.py build_ext --inplace -j 16`
- Smoke check: `cd /work && python -c "import statsmodels.api as sm, statsmodels.tsa.api; print(\"import ok\")"`
- Tests: write your own or run existing tests as needed, e.g. `python -m pytest <test path>`.

## Acceptance

1. The grader rebuilds from the start snapshot + your changes in the same image (offline), then runs a set of hidden pytest tests (covering the behavior of the interfaces above, numerical correctness, agreement with reference implementations / reference software results, edge cases and error handling).
2. Scoring: the reward is 1 only if all hidden tests pass, otherwise 0; the pass fraction is also reported for reference. A build failure or import failure scores 0.
3. Existing tests in the repository related to this feature must keep passing; do not modify existing tests or build dependencies, and do not remove existing public interfaces.
4. Submit source changes only (a patch or the modified working directory).

## Notes

You may decompose the task yourself, develop in parallel and integrate. The evaluation records time, model and tool usage, and delivery/integration status; no particular number of branches or implementation route is required.
