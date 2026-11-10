> The working directory is `/workspace`. The starting repository is at `/workspace/qutip/` (source tree, no git history); it has already been built/installed with the commands in `environment.md` and can be imported directly. The interface specification is in `/workspace/interface/`, and the environment description is in `/workspace/environment.md`.
> Deliverable: modify / add source code directly in `/workspace/qutip/`. For grading, the whole `/workspace/qutip/` directory is collected; in a separate grading environment the build products are removed, the repository is rebuilt, and then the hidden tests are put in place and run. To rebuild / run the import check, execute `bash -c '. /opt/wfs/build.sh && do_install && do_import'`. The repository is installed in editable mode (`pip install -e .`).
> There is no network access at run time.

# Implement a multi-bath hierarchical equations of motion (HEOM) solver for QuTiP

## Background and goal

QuTiP currently only has an HEOM solver that supports a single Drude-Lorentz bosonic bath (`qutip.nonmarkov.heom.HSolverDL`; the old implementation is kept unchanged in
`qutip/nonmarkov/dlheom_solver.py`). Implement a general HEOM framework:

1. Describe baths by "exponential expansion terms of the bath correlation function" (exponents): bosonic baths distinguish real-part / imaginary-part / combined real-and-imaginary terms (types R, I, RI), fermionic baths distinguish `+`/`-` terms;
   support merging identical terms by frequency; provide constructors for Drude-Lorentz (Matsubara expansion, optional terminator correction), Drude-Lorentz Padé expansion, underdamped bosonic baths, and generic fermionic baths.
2. A labelling/indexing scheme for the hierarchy's auxiliary density operators (ADOs): given a set of exponents and a maximum depth, enumerate all ADO labels; support idx/next/prev and filtering by level, label and type.
3. Assemble the HEOM right-hand side (a block-sparse Liouvillian matrix), supporting several bosonic baths and several fermionic baths at the same time (fermionic terms must handle parity/signs correctly);
   implement time evolution `run` (optionally returning all ADO states) and the steady state `steady_state`.
4. Re-implement `HSolverDL`, compatible with the old interface, on top of the new framework, and make `qutip.nonmarkov.heom` export the new interface.

## Starting point

The workspace is a fixed version of the `QuTiP (qutip/qutip)` repository (source tree, no git history). The functionality described above does **not exist** in the starting point; you need to implement it.
The rest of the repository (existing modules, build system, existing tests) can be used directly.

## Required interfaces

- `qutip/nonmarkov/bofin_baths.py`: `BathExponent` (including the `types` enumeration), `Bath`, `BosonicBath` (including the `combine` class method), `DrudeLorentzBath` (including `terminator()`), `DrudeLorentzPadeBath`, `UnderDampedBath`, `FermionicBath`
- `qutip/nonmarkov/bofin_solvers.py`: `HierarchyADOs`, `HierarchyADOsState`, `HEOMSolver` (`run`, `steady_state`), `HSolverDL`
- `qutip/nonmarkov/heom.py`: export the public classes above (`__all__`)

The complete interface specification (signatures and docstrings, function bodies omitted) is in the `interface/` directory; its directory layout mirrors the target file paths in the repository one to one
(`*.stub.py` / `*.stub.pyx` correspond to the `.py` / `.pyx` files of the same name in the repository).
All public classes, functions, methods, attributes, parameter names and default values that appear in `interface/` are within the scope of grading; internal helper functions that are not listed may be designed freely.
The numerical conventions described in the docstrings (units, signs, normalization, ordering, return types and shapes) must be followed.

## Allowed modifications

- `qutip/nonmarkov/bofin_baths.py (new)`
- `qutip/nonmarkov/bofin_solvers.py (new)`
- `qutip/nonmarkov/heom.py (changed to export the new interface)`
- `new private helper modules under qutip/nonmarkov/`

Do not modify the existing test files of the repository or modules unrelated to the target; at grading time the test directories are overwritten with the hidden tests and the hashes of protected files are checked.
You may add private helper modules (within the allowed scope above).

## Environment and constraints

- Python 3.9 (Docker base image `python:3.9-bookworm`)
- Python dependencies (resolved to versions released before 2021-11-23): `numpy<1.20 scipy<1.8 cython<3 setuptools<60 wheel packaging pytest pytest-rerunfailures`
- Build/install commands: see `environment.md`.
- **No network access**: do not download or install additional packages, and do not obtain a ready-made implementation of this functionality from the network; use only the starting repository and the dependencies listed above.


## Grading

The hidden tests cover: the exponents produced by each bath constructor (coefficients, frequencies, types, merging rules, terminator); ADO enumeration and filtering; time evolution and steady states with single/multiple bosonic baths and fermionic baths (including currents and populations compared with analytic / numerically integrated results); `HSolverDL` compatibility. Test files: `qutip/tests/test_bofin_baths.py`, `test_bofin_solvers.py`, `test_heom.py`.

Grading runs in a fixed Docker environment: your submission is first built/installed, then the hidden tests are put in place and run. Full success requires all hidden tests to pass;
the pass fraction is reported as well. Numerical comparisons use the tolerances built into the hidden tests.

## How to work

You may decompose the task yourself, run several lines of work in parallel and integrate them at the end; grading does not prescribe the number of branches or the implementation route, only the final submission counts.
