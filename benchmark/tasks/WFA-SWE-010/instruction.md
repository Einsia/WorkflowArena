> **Harbor path notes**
> - The start source snapshot is at `/work` (the "working directory `/work`" in the statement below). It has already been built and installed with the build command given below and can be imported directly.
> - The files `INTERFACE.md`, `MANIFEST.md` and `env/Dockerfile` mentioned in the statement are under `/workspace/` ("`INTERFACE.md` in the same directory" means `/workspace/INTERFACE.md`).
> - Deliverable: the `/work` directory itself. At the end, the grader collects the whole `/work` source tree, deletes compiled build products that are not part of the start tree (`*.so`, `*.o`, `build/`, `*.egg-info`, Cython-generated C/C++ files, etc.), then rebuilds it offline in a separate image and runs the hidden tests. No separate patch file is needed.
> - There is no network access at run time.

# Autoregressive distributed lag (ARDL) models

Implement the new functionality described below in the provided fixed-version `statsmodels` source snapshot (working directory `/work`, without git history).

## Background

The ARDL (Autoregressive Distributed Lag) model regresses the dependent variable on its own lags together with the current and lagged values of several exogenous variables; it is the basis of cointegration / error-correction analysis and dynamic-multiplier analysis. The repository already has `AutoReg` (`statsmodels/tsa/ar_model.py`) and the deterministic-term tool `DeterministicProcess`, but no ARDL model that specifies lag orders per exogenous column.

## Required deliverables

1. New module `statsmodels/tsa/ardl.py` providing `ARDL`, `ARDLResults`, `ardl_select_order` and the order-selection results object (see `INTERFACE.md`). `ARDL` should be implemented as an extension of `AutoReg` (sharing the trend/seasonal/deterministic-term and hold_back semantics).
2. Support: several forms for `lags`/`order` -- int, sequence, dict (by column name or column index); `causal`; `fixed` non-lagged regressors; pandas and ndarray input; parameter naming rules (lags of the dependent variable look like `<name>.L<k>`, exogenous variables look like `<name>.L<k>`, with the current period as `L0`; for ndarray input the column names are `x0, x1, ...` and fixed regressors are `z.0, z.1, ...`, consistent with the existing naming style of `AutoReg`).
3. `ARDLResults`: `predict`/`forecast` (requiring out-of-sample values of the exogenous variables `exog_oos`, supporting `dynamic`), `get_prediction` (mean and confidence intervals), `plot_predict`, `summary`; `ARDL.from_formula`.
4. `ardl_select_order`: given maximum orders, select the lag orders of the dependent variable and of each exogenous variable by `aic`/`bic`/`hqic`, returning a results object with attributes such as `model`, the `aic`/`bic`/`hqic` rankings, and `ar_lags`/`dl_lags`.
5. Exports: `from statsmodels.tsa.api import ARDL, ardl_select_order` works.
6. You may refactor the internals of `AutoReg` as needed (e.g. factor out shared helper functions for prediction / dynamic parsing / plotting), but the existing public behavior of `AutoReg` and the existing tests must be preserved.

The complete target interface (signatures + docstring-level descriptions) is in `INTERFACE.md` in the same directory. Function bodies are omitted; the behavior described by the docstrings is the acceptance criterion. Names marked "internal interface used directly by the tests" must also be provided with the same name and the same signature.

## Allowed scope of changes

- You may add `statsmodels/tsa/ardl.py` and other new modules; you may modify `statsmodels/tsa/ar_model.py`, `statsmodels/tsa/tsatools.py`, `statsmodels/tsa/api.py`, and the compatibility code in `statsmodels/compat/python.py`.
- The start tree already provides the example dataset `statsmodels.datasets.danish_data` (Danish money-demand data, used by the tests).
- Every other file of the start tree is hash-protected, including test helpers (e.g. `_testutils` modules), `conftest.py` files, build scripts and packaging configuration not listed above: modifying or deleting any of them, or replacing it with a symlink, scores 0. New files may be added, except files named `conftest.py`, `pytest.ini`, `tox.ini`, `setup.cfg`, `pyproject.toml`, `sitecustomize.py`, `usercustomize.py` or `*.pth`, and except symlinks.
- Do not modify existing test files or build dependencies; do not access the network to obtain the upstream implementation.

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
