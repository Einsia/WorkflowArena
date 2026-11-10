> **Harbor path notes**
> - The start source snapshot is at `/work` (the "working directory `/work`" in the statement below). It has already been built and installed with the build command given below and can be imported directly.
> - The files `INTERFACE.md`, `MANIFEST.md` and `env/Dockerfile` mentioned in the statement are under `/workspace/` ("`INTERFACE.md` in the same directory" means `/workspace/INTERFACE.md`).
> - Deliverable: the `/work` directory itself. At the end, the grader collects the whole `/work` source tree, deletes compiled build products that are not part of the start tree (`*.so`, `*.o`, `build/`, `*.egg-info`, Cython-generated C/C++ files, etc.), then rebuilds it offline in a separate image and runs the hidden tests. No separate patch file is needed.
> - There is no network access at run time.

# Generic masked array class (Masked)

Implement the new functionality described below in the provided fixed-version `astropy` source snapshot (working directory `/work`, without git history).

## Background

`numpy.ma.MaskedArray` does not combine well with ndarray subclasses such as `Quantity`. What is needed is a masking mixin: `Masked(data, mask)` automatically generates the corresponding masked subclass for the data's type (e.g. `MaskedQuantity`), propagates the mask correctly through ufuncs, reductions and numpy functions (`__array_function__`), and can be put into containers such as `QTable`.

## Required deliverables

1. New subpackage `astropy/utils/masked/`: the `Masked` factory base class and `MaskedNDArray` in `core.py` (plus automatic subclass generation per data class, `unmasked`, `mask`, `filled`, `from_unmasked`, etc.); the classification and override tables for numpy functions in `function_helpers.py` (`MASKED_SAFE_FUNCTIONS`, `APPLY_TO_BOTH_FUNCTIONS`, `DISPATCHED_FUNCTIONS`, `UNSUPPORTED_FUNCTIONS`, `IGNORED_FUNCTIONS`); the tests directly check that these sets cover all numpy functions.
2. Semantics: in ufuncs the mask propagates as "the output is masked if any input is masked" (including `out=`, `where=`, reduce/accumulate/outer); reductions (sum/mean/var/std/min/max/argmin/argsort/sort/median/quantile, etc.) ignore masked elements; comparisons, indexing, `__setitem__`, views and shape operations act on both data and mask; `repr/str` show masked elements as `———`.
3. Integration with `Quantity` (`Masked(Quantity)` supports unit conversion and ufuncs), `Longitude`/`Angle`, `Table/QTable` serialization (`astropy/table/serialize.py`) and `astropy/utils/shapes.py` (factor the shape-related methods out into a reusable mixin used by Masked).

The complete target interface (signatures + docstring-level descriptions) is in `INTERFACE.md` in the same directory. Function bodies are omitted; the behavior described by the docstrings is the acceptance criterion. Names marked "internal interface used directly by the tests" must also be provided with the same name and the same signature.

## Allowed scope of changes

- You may add the `astropy/utils/masked/` subpackage, and modify the integration-related parts of `astropy/utils/shapes.py`, `astropy/units/quantity.py`, `astropy/units/quantity_helper/converters.py`, `astropy/table/serialize.py`, `astropy/coordinates/angles.py`.
- Every other file of the start tree is hash-protected, including test helpers (e.g. `_testutils` modules), `conftest.py` files, build scripts and packaging configuration not listed above: modifying or deleting any of them, or replacing it with a symlink, scores 0. New files may be added, except files named `conftest.py`, `pytest.ini`, `tox.ini`, `setup.cfg`, `pyproject.toml`, `sitecustomize.py`, `usercustomize.py` or `*.pth`, and except symlinks.
- Do not modify existing tests or build dependencies; do not access the network.

## Environment and commands

- Environment: the image described by `env/Dockerfile` (dependency versions pinned to the repository's ecosystem at that time); working directory `/work`; no network during evaluation.
- Build: `export SETUPTOOLS_SCM_PRETEND_VERSION=4.3.dev0 ; cd /work && pip install --no-build-isolation --no-deps -e . -q`
- Smoke check: `export LD_PRELOAD=/usr/lib/x86_64-linux-gnu/faketime/libfaketime.so.1 FAKETIME_DONT_FAKE_MONOTONIC=1 FAKETIME="@2021-04-14 12:00:00" && cd /work && python -c "import astropy, astropy.units, astropy.coordinates, astropy.timeseries; print(\"import ok\", astropy.__version__)"`
- Tests: write your own or run existing tests as needed, e.g. `python -m pytest <test path>`.

## Acceptance

1. The grader rebuilds from the start snapshot + your changes in the same image (offline), then runs a set of hidden pytest tests (covering the behavior of the interfaces above, numerical correctness, agreement with reference implementations / reference software results, edge cases and error handling).
2. Scoring: the reward is 1 only if all hidden tests pass, otherwise 0; the pass fraction is also reported for reference. A build failure or import failure scores 0.
3. Existing tests in the repository related to this feature must keep passing; do not modify existing tests or build dependencies, and do not remove existing public interfaces.
4. Submit source changes only (a patch or the modified working directory).

## Notes

You may decompose the task yourself, develop in parallel and integrate. The evaluation records time, model and tool usage, and delivery/integration status; no particular number of branches or implementation route is required.
