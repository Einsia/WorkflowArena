> **Harbor path notes**
> - The start source snapshot is at `/work` (the "working directory `/work`" in the statement below). It has already been built and installed with the build command given below and can be imported directly.
> - The files `INTERFACE.md`, `MANIFEST.md` and `env/Dockerfile` mentioned in the statement are under `/workspace/` ("`INTERFACE.md` in the same directory" means `/workspace/INTERFACE.md`).
> - Deliverable: the `/work` directory itself. At the end, the grader collects the whole `/work` source tree, deletes compiled build products that are not part of the start tree (`*.so`, `*.o`, `build/`, `*.egg-info`, Cython-generated C/C++ files, etc.), then rebuilds it offline in a separate image and runs the hidden tests. No separate patch file is needed.
> - There is no network access at run time.

# New infrastructure for continuous probability distributions (ContinuousDistribution)

Implement the new functionality described below in the provided fixed-version `scipy` source snapshot (working directory `/work`, without git history).

## Background

The parameter handling, broadcasting and numerical strategies of `scipy.stats.rv_continuous` have long been hard to extend. The new design is centered on "distribution object = parameterization + a set of overridable basic functions": for each statistical function (pdf/logpdf/cdf/logcdf/ccdf/logccdf/icdf/iccdf/ilogcdf, moments of each order, entropy, mode, median, sampling) it provides several evaluation methods, and when a formula is missing it automatically falls back to log space, the complement, numerical integration (tanh-sinh) or numerical inversion; it also supports broadcasting of parameter arrays, returning NaN for out-of-domain parameters, and location-scale transformation.

## Required deliverables

1. New module `scipy/stats/_distribution_infrastructure.py`: domains and parameters (`_Domain`, `_SimpleDomain`/`_RealDomain`, `_Parameter`/`_RealParameter`, `_Parameterization`); the `ContinuousDistribution` base class (construction / parameter validation / broadcasting, `support`, `pdf/logpdf/cdf/logcdf/ccdf/logccdf/icdf/iccdf/ilogcdf/ilogccdf` (including the two-argument interval form `cdf(x, y)`), `moment(order, kind=...)`, `mean/median/mode/variance/standard_deviation/skewness/kurtosis/entropy/logentropy`, `sample(shape, method=..., rng=...)` (including inverse transform and QMC), the `method=` keyword for selecting the evaluation strategy, `cache_policy`/`validation_policy`/`tol`); `ShiftedScaledDistribution` (`loc`/`scale` transformation and operator overloading `+ - * /`); `_fiinfo`, `_generate_domain_support`, etc., which the tests import directly (see `INTERFACE.md`).
2. New module `scipy/stats/_new_distributions.py`: `StandardNormal`, `Normal` (parameterized by `mu`, `sigma`), and `_LogUniform`, `_Uniform`, which the tests use; `Normal` is exported from `scipy.stats`.
3. Necessary supporting changes: `scipy/integrate/_tanhsinh.py` (small changes used for log-space integration, etc.), `scipy/stats/_fit.py`, `scipy/stats/meson.build` (install the new modules and `_new_distribution_docs.json`).

The complete target interface (signatures + docstring-level descriptions) is in `INTERFACE.md` in the same directory. Function bodies are omitted; the behavior described by the docstrings is the acceptance criterion. Names marked "internal interface used directly by the tests" must also be provided with the same name and the same signature.

## Allowed scope of changes

- You may add the modules above and modify `scipy/stats/__init__.py`, `scipy/stats/meson.build`, `scipy/stats/_fit.py`, `scipy/integrate/_tanhsinh.py`.
- Every other file of the start tree is hash-protected, including test helpers (e.g. `_testutils` modules), `conftest.py` files, build scripts and packaging configuration not listed above: modifying or deleting any of them, or replacing it with a symlink, scores 0. New files may be added, except files named `conftest.py`, `pytest.ini`, `tox.ini`, `setup.cfg`, `pyproject.toml`, `sitecustomize.py`, `usercustomize.py` or `*.pth`, and except symlinks.
- Do not modify existing tests or build dependencies; do not access the network.

## Environment and commands

- Environment: the image described by `env/Dockerfile` (dependency versions pinned to the repository's ecosystem at that time); working directory `/work`; no network during evaluation.
- Build: `cd /work && pip install --no-build-isolation --no-deps -q -Ccompile-args=-j24 . `
- Smoke check: `cd / && python -c "import scipy, scipy.stats, scipy.signal, scipy.interpolate; print(\"import ok\", scipy.__version__)"`
- Tests: write your own or run existing tests as needed, e.g. `python -m pytest <test path>`.

## Acceptance

1. The grader rebuilds from the start snapshot + your changes in the same image (offline), then runs a set of hidden pytest tests (covering the behavior of the interfaces above, numerical correctness, agreement with reference implementations / reference software results, edge cases and error handling).
2. Scoring: the reward is 1 only if all hidden tests pass, otherwise 0; the pass fraction is also reported for reference. A build failure or import failure scores 0.
3. Existing tests in the repository related to this feature must keep passing; do not modify existing tests or build dependencies, and do not remove existing public interfaces.
4. Submit source changes only (a patch or the modified working directory).

## Notes

You may decompose the task yourself, develop in parallel and integrate. The evaluation records time, model and tool usage, and delivery/integration status; no particular number of branches or implementation route is required.
