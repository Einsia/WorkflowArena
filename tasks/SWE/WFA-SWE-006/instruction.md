> **Harbor path notes**
> - The start source snapshot is at `/work` (the "working directory `/work`" in the statement below). It has already been built and installed with the build command given below and can be imported directly.
> - The files `INTERFACE.md`, `MANIFEST.md` and `env/Dockerfile` mentioned in the statement are under `/workspace/` ("`INTERFACE.md` in the same directory" means `/workspace/INTERFACE.md`).
> - Deliverable: the `/work` directory itself. At the end, the grader collects the whole `/work` source tree, deletes compiled build products that are not part of the start tree (`*.so`, `*.o`, `build/`, `*.egg-info`, Cython-generated C/C++ files, etc.), then rebuilds it offline in a separate image and runs the hidden tests. No separate patch file is needed.
> - There is no network access at run time.

# Quasi-Monte Carlo (QMC) sampling submodule scipy.stats.qmc

Implement the new functionality described below in the provided fixed-version `scipy` source snapshot (working directory `/work`, without git history).

## Background

Quasi-Monte Carlo methods use low-discrepancy sequences instead of pseudo-random numbers to perform numerical integration and design of experiments with faster convergence. The start version of SciPy has no QMC samplers. The start tree already provides the Sobol sequence direction-number data in `scipy/stats/_sobol_direction_numbers.npz` (Joe & Kuo, 21201 dimensions).

## Required deliverables

1. Public submodule `scipy.stats.qmc` (`scipy/stats/qmc.py`; the implementation may live in `scipy/stats/_qmc.py`), usable via `from scipy.stats import qmc`, exporting `QMCEngine`, `Sobol`, `Halton`, `OrthogonalLatinHypercube`, `LatinHypercube`, `MultinomialQMC`, `MultivariateNormalQMC`, `discrepancy`, `update_discrepancy`, `scale` (interface in `INTERFACE.md`).
2. `QMCEngine(d, seed=None)`: `random(n)`, `reset()`, `fast_forward(n)`, keeping track of `num_generated`; reproducible random-seed semantics.
3. `Sobol(d, scramble=True, seed=None)`: Cython extension `scipy/stats/_sobol.pyx` (direction-number initialization, Gray-code generation, LMS + digital-shift scrambling, `random_base2(m)`), registering the extension and data file in `scipy/stats/setup.py`; the tests call `_sobol._test_find_index` directly.
4. `Halton` (with scrambling) and the helper functions `van_der_corput`, `primes_from_2_to`, `n_primes` (imported directly by the tests).
5. `discrepancy(sample, iterative=False, method="CD")` supporting `CD`, `WD`, `MD`, `L2-star`; `update_discrepancy`; `scale(sample, l_bounds, u_bounds, reverse=False)`.

The complete target interface (signatures + docstring-level descriptions) is in `INTERFACE.md` in the same directory. Function bodies are omitted; the behavior described by the docstrings is the acceptance criterion. Names marked "internal interface used directly by the tests" must also be provided with the same name and the same signature.

## Allowed scope of changes

- You may add `scipy/stats/qmc.py`, `scipy/stats/_qmc.py`, `scipy/stats/_qmc.pyi`, `scipy/stats/_sobol.pyx`, and modify `scipy/stats/__init__.py`, `scipy/stats/setup.py`.
- Every other file of the start tree is hash-protected, including test helpers (e.g. `_testutils` modules), `conftest.py` files, build scripts and packaging configuration not listed above: modifying or deleting any of them, or replacing it with a symlink, scores 0. New files may be added, except files named `conftest.py`, `pytest.ini`, `tox.ini`, `setup.cfg`, `pyproject.toml`, `sitecustomize.py`, `usercustomize.py` or `*.pth`, and except symlinks.
- Do not modify existing tests or build dependencies; do not access the network.

## Environment and commands

- Environment: the image described by `env/Dockerfile` (dependency versions pinned to the repository's ecosystem at that time); working directory `/work`; no network during evaluation.
- Build: `cd /work && export FFLAGS=-fallow-argument-mismatch NPY_NUM_BUILD_JOBS=16 && python setup.py build_ext --inplace -j 16`
- Smoke check: `cd /work && python -c "import scipy, scipy.stats, scipy.optimize; print(\"import ok\", scipy.__version__)"`
- Tests: write your own or run existing tests as needed, e.g. `python -m pytest <test path>`.

## Acceptance

1. The grader rebuilds from the start snapshot + your changes in the same image (offline), then runs a set of hidden pytest tests (covering the behavior of the interfaces above, numerical correctness, agreement with reference implementations / reference software results, edge cases and error handling).
2. Scoring: the reward is 1 only if all hidden tests pass, otherwise 0; the pass fraction is also reported for reference. A build failure or import failure scores 0.
3. Existing tests in the repository related to this feature must keep passing; do not modify existing tests or build dependencies, and do not remove existing public interfaces.
4. Submit source changes only (a patch or the modified working directory).

## Notes

You may decompose the task yourself, develop in parallel and integrate. The evaluation records time, model and tool usage, and delivery/integration status; no particular number of branches or implementation route is required.
