> **Harbor path notes**
> - The start source snapshot is at `/work` (the "working directory `/work`" in the statement below). It has already been built and installed with the build command given below and can be imported directly.
> - The files `INTERFACE.md`, `MANIFEST.md` and `env/Dockerfile` mentioned in the statement are under `/workspace/` ("`INTERFACE.md` in the same directory" means `/workspace/INTERFACE.md`).
> - Deliverable: the `/work` directory itself. At the end, the grader collects the whole `/work` source tree, deletes compiled build products that are not part of the start tree (`*.so`, `*.o`, `build/`, `*.egg-info`, Cython-generated C/C++ files, etc.), then rebuilds it offline in a separate image and runs the hidden tests. No separate patch file is needed.
> - There is no network access at run time.

# Truncated count models and hurdle models

Implement the new functionality described below in the provided fixed-version `statsmodels` source snapshot (working directory `/work`, without git history).

## Background

In count data, the mechanism generating zeros often differs from that of positive counts. A hurdle model describes "whether the count is zero" with a binary/censored model, and the positive counts with a zero-truncated count model; left-truncated count models are also commonly used on their own for samples where only y>=k is observed. The repository's `statsmodels/discrete/` already has Poisson, NegativeBinomialP, zero-inflated models, etc., but no truncated/censored/hurdle count models.

## Required deliverables

1. New module `statsmodels/discrete/truncated_model.py`: the generic left-truncated model base class `TruncatedLFGeneric` and `TruncatedLFPoisson`, `TruncatedLFNegativeBinomialP`, `TruncatedLFGeneralizedPoisson` (parameter `truncation`, zero-truncation by default); right-censored (censored at 0/1) helper models; `HurdleCountModel(endog, exog, dist="poisson", zerodist="poisson", p=2, pzero=2, ...)`; the corresponding results classes.
2. Model methods: `loglike`/`loglikeobs`/`score_obs`/`score`/`hessian`, `fit`, `fit_regularized`, `predict` (`which` supports at least `"mean"`, `"linear"`, `"mean-main"`, `"prob"`, `"prob-zero"`, `"prob-main"`, etc.; see the docstrings in INTERFACE).
3. Distributions: add `truncatedpoisson` and `truncatednegbin` (in the style of scipy.stats discrete distributions) to `statsmodels/distributions/discrete.py`, exported from `statsmodels.distributions`.
4. `statsmodels.api` exports `TruncatedLFPoisson`, `TruncatedLFNegativeBinomialP`, `HurdleCountModel`.
5. You may add generic functionality needed by the base models to `statsmodels/discrete/discrete_model.py` (e.g. predicted probabilities / truncated moments), but must not break the behavior of existing models.

The complete target interface (signatures + docstring-level descriptions) is in `INTERFACE.md` in the same directory. Function bodies are omitted; the behavior described by the docstrings is the acceptance criterion. Names marked "internal interface used directly by the tests" must also be provided with the same name and the same signature.

## Allowed scope of changes

- You may add `statsmodels/discrete/truncated_model.py` and modify `statsmodels/discrete/discrete_model.py`, `statsmodels/distributions/discrete.py`, `statsmodels/distributions/__init__.py`, `statsmodels/api.py`.
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
