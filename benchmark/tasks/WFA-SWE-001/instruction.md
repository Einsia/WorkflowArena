> **Harbor path notes**
> - The start source snapshot is at `/work` (the "working directory `/work`" in the statement below). It has already been built and installed with the build command given below and can be imported directly.
> - The files `INTERFACE.md`, `MANIFEST.md` and `env/Dockerfile` mentioned in the statement are under `/workspace/` ("`INTERFACE.md` in the same directory" means `/workspace/INTERFACE.md`).
> - Deliverable: the `/work` directory itself. At the end, the grader collects the whole `/work` source tree, deletes compiled build products that are not part of the start tree (`*.so`, `*.o`, `build/`, `*.egg-info`, Cython-generated C/C++ files, etc.), then rebuilds it offline in a separate image and runs the hidden tests. No separate patch file is needed.
> - There is no network access at run time.

# Spectral coordinates (SpectralCoord / SpectralQuantity) and their integration with reference frames and WCS

Implement the new functionality described below in the provided fixed-version `astropy` source snapshot (working directory `/work`, without git history).

## Background

The values on a spectral axis (frequency / wavelength / energy / wavenumber / velocity) depend on the motion of the observer and the target. What is needed is a spectral coordinate object that behaves like a Quantity but also carries the observer and target coordinates and a Doppler convention, can apply correct relativistic Doppler corrections between different rest frames (e.g. barycentric, LSRK), and to which the spectral axes of FITS-WCS (keywords SPECSYS/SSYSOBS/RESTFRQ, etc.) are mapped.

## Required deliverables

1. `astropy/coordinates/spectral_quantity.py`: `SpectralQuantity` (a Quantity subclass for spectral units, with `doppler_convention` and `doppler_rest`; `to()` automatically uses the spectral/Doppler equivalencies).
2. `astropy/coordinates/spectral_coordinate.py`: `SpectralCoord` (`observer`, `target`, `radial_velocity`, `redshift`, `with_observer_stationary_relative_to`, `with_radial_velocity_shift`, `to_rest`, etc.), plus `_apply_relativistic_doppler_shift`, which the tests use directly; `SpectralCoord`/`SpectralQuantity` are exported from `astropy.coordinates`.
3. `astropy/coordinates/builtin_frames/lsr.py`: add the `LSRK` and `LSRD` frames and their transformations to/from ICRS, exported from `astropy.coordinates`.
4. WCS integration: in `astropy/wcs/wcsapi/fitswcs.py`, `world_axis_object_classes` for spectral axes returns `SpectralCoord`, constructing the observer/target from keywords such as SPECSYS, SSYSOBS, MJD-OBS, OBSGEO-*, RADESYS, VELOSYS, ZSOURCE; related helpers in `astropy/wcs/wcs.py` (e.g. `WCSSUB_LONGITUDE/LATITUDE` sub-axis selection); the `VELOCITY_FRAMES` mapping.
5. ASDF: tag and schema for `SpectralCoord` (`astropy/io/misc/asdf/`).

The complete target interface (signatures + docstring-level descriptions) is in `INTERFACE.md` in the same directory. Function bodies are omitted; the behavior described by the docstrings is the acceptance criterion. Names marked "internal interface used directly by the tests" must also be provided with the same name and the same signature.

## Allowed scope of changes

- You may add the modules above and modify `astropy/coordinates/__init__.py`, `builtin_frames/__init__.py`, `builtin_frames/lsr.py`, `sky_coordinate.py`, `astropy/wcs/wcs.py`, `astropy/wcs/wcsapi/fitswcs.py`, and the extension registration in `astropy/io/misc/asdf/extension.py` (new schema / tag files under `astropy/io/misc/asdf/` may be added).
- Every other file of the start tree is hash-protected, including test helpers (e.g. `_testutils` modules), `conftest.py` files, build scripts and packaging configuration not listed above: modifying or deleting any of them, or replacing it with a symlink, scores 0. New files may be added, except files named `conftest.py`, `pytest.ini`, `tox.ini`, `setup.cfg`, `pyproject.toml`, `sitecustomize.py`, `usercustomize.py` or `*.pth`, and except symlinks.
- Do not modify existing tests or build dependencies; do not access the network (test cases that need the network will be skipped).

## Environment and commands

- Environment: the image described by `env/Dockerfile` (dependency versions pinned to the repository's ecosystem at that time); working directory `/work`; no network during evaluation.
- Build: `export SETUPTOOLS_SCM_PRETEND_VERSION=4.1.dev0 CFLAGS=-O0; cd /work && pip install --no-build-isolation --no-deps -e . -q`
- Smoke check: `export LD_PRELOAD=/usr/lib/x86_64-linux-gnu/faketime/libfaketime.so.1 FAKETIME_DONT_FAKE_MONOTONIC=1 FAKETIME="@2020-05-02 12:00:00" && cd /work && python -c "import astropy, astropy.units, astropy.coordinates, astropy.timeseries; print(\"import ok\", astropy.__version__)"`
- Tests: write your own or run existing tests as needed, e.g. `python -m pytest <test path>`.

## Acceptance

1. The grader rebuilds from the start snapshot + your changes in the same image (offline), then runs a set of hidden pytest tests (covering the behavior of the interfaces above, numerical correctness, agreement with reference implementations / reference software results, edge cases and error handling).
2. Scoring: the reward is 1 only if all hidden tests pass, otherwise 0; the pass fraction is also reported for reference. A build failure or import failure scores 0.
3. Existing tests in the repository related to this feature must keep passing; do not modify existing tests or build dependencies, and do not remove existing public interfaces.
4. Submit source changes only (a patch or the modified working directory).

## Notes

You may decompose the task yourself, develop in parallel and integrate. The evaluation records time, model and tool usage, and delivery/integration status; no particular number of branches or implementation route is required.
