> The working directory is `/workspace`. The starting repository is at `/workspace/pyscf/` (source tree, no git history); it has already been built/installed with the commands in `environment.md` and can be imported directly. The interface specification is in `/workspace/interface/`, and the environment description is in `/workspace/environment.md`.
> Deliverable: modify / add source code directly in `/workspace/pyscf/`. For grading, the whole `/workspace/pyscf/` directory is collected; in a separate grading environment the build products are removed, the repository is rebuilt, and then the hidden tests are put in place and run. To rebuild / run the import check, execute `bash -c '. /opt/wfs/build.sh && do_install && do_import'`. `PYTHONPATH=/workspace/pyscf` is set in the image, the C extensions have been built in `pyscf/lib/build`, and the third-party libraries (libcint/libxc/xcfun) have been pre-fetched, so the command above also works offline for rebuilding.
> There is no network access at run time.

# Implement molecular self-consistent GW methods (evGW, qsGW) and exact / contour-deformation G0W0 for PySCF

## Background and goal

PySCF's `pyscf.gw` currently has analytic-continuation G0W0 (`gw_ac`/`ugw_ac`), exact G0W0 (`gw_exact`, without density fitting), and an old contour-deformation implementation. Implement:

1. **Exact G0W0 (density fitting)**: `GWExactDF`/`UGWExactDF` — build and diagonalize the particle-hole RPA (direct RPA) from density-fitted three-center integrals to obtain the neutral excitations and transition densities,
   the full-frequency self-energy (analytic pole form), the solution of the quasiparticle equation (linearized or graphical/iterative), the Green's function and the density of states.
2. **Contour-deformation G0W0**: rewrite `GWCD` and add `UGWCD` (real-axis polarizability + imaginary-axis integration + residues).
3. **Eigenvalue self-consistent evGW**: `EVGW`/`UEVGW` (based on the analytic-continuation self-energy) and `EVGWExact`/`UEVGWExact` (based on the exact self-energy), iteratively updating the quasiparticle energies until convergence.
4. **Quasiparticle self-consistent qsGW**: `QSGW`/`UQSGW` and `QSGWExact`/`UQSGWExact`, which build a Hermitized static self-energy and iteratively update the orbitals and energies.

All classes follow the interface conventions of the PySCF GW classes (`kernel`, `mo_energy`, `mo_coeff`, `frozen`, `orbs`, `nmom_max`, etc.); results must agree with the reference values to within meV.

## Starting point

The workspace is a fixed version of the `PySCF (pyscf/pyscf)` repository (source tree, no git history). The functionality described above does **not exist** in the starting point; you need to implement it.
The rest of the repository (existing modules, build system, existing tests) can be used directly.

## Required interfaces

- `pyscf/gw/gw_exact_df.py`, `ugw_exact_df.py`: `GWExactDF`, `UGWExactDF` (and `diagonalize_phrpa`, `get_sigma`, `make_gf`, etc.)
- `pyscf/gw/gw_cd.py` (rewritten), `ugw_cd.py`: `GWCD`, `UGWCD`
- `pyscf/gw/evgw.py`, `uevgw.py`, `evgw_exact.py`, `uevgw_exact.py`: `EVGW`, `UEVGW`, `EVGWExact`, `UEVGWExact`
- `pyscf/gw/qsgw.py`, `uqsgw.py`, `qsgw_exact.py`, `uqsgw_exact.py`: `QSGW`, `UQSGW`, `QSGWExact`, `UQSGWExact`

The complete interface specification (signatures and docstrings, function bodies omitted) is in the `interface/` directory; its directory layout mirrors the target file paths in the repository one to one
(`*.stub.py` / `*.stub.pyx` correspond to the `.py` / `.pyx` files of the same name in the repository).
All public classes, functions, methods, attributes, parameter names and default values that appear in `interface/` are within the scope of grading; internal helper functions that are not listed may be designed freely.
The numerical conventions described in the docstrings (units, signs, normalization, ordering, return types and shapes) must be followed.

## Allowed modifications

- `the files listed above under pyscf/gw/ (new or rewritten)`
- `new private helper modules under pyscf/gw/`

Do not modify the existing test files of the repository or modules unrelated to the target; at grading time the test directories are overwritten with the hidden tests and the hashes of protected files are checked.
You may add private helper modules (within the allowed scope above).

## Environment and constraints

- Python 3.12 (Docker base image `python:3.12-bookworm`)
- System packages: `cmake libopenblas-dev`
- Python dependencies (resolved to versions released before 2026-07-14): `numpy scipy h5py pytest pytest-xdist pytest-timeout`
- Build/install commands: see `environment.md`.
- **No network access**: do not download or install additional packages, and do not obtain a ready-made implementation of this functionality from the network; use only the starting repository and the dependencies listed above.


## Grading

The hidden tests cover: HOMO/LUMO quasiparticle energies of small molecules such as H2O with each method (compared with reference values), R/U consistency, frozen orbitals, and consistency between the exact and analytic-continuation results. Test files: `pyscf/gw/test/test_*gw*.py` (13 files).

Grading runs in a fixed Docker environment: your submission is first built/installed, then the hidden tests are put in place and run. Full success requires all hidden tests to pass;
the pass fraction is reported as well. Numerical comparisons use the tolerances built into the hidden tests.

## How to work

You may decompose the task yourself, run several lines of work in parallel and integrate them at the end; grading does not prescribe the number of branches or the implementation route, only the final submission counts.
