> **Harbor path notes**
> - The start source snapshot is at `/work` (the "working directory `/work`" in the statement below). It has already been built and installed with the build command given below and can be imported directly.
> - The files `INTERFACE.md`, `MANIFEST.md` and `env/Dockerfile` mentioned in the statement are under `/workspace/` ("`INTERFACE.md` in the same directory" means `/workspace/INTERFACE.md`).
> - Deliverable: the `/work` directory itself. At the end, the grader collects the whole `/work` source tree, deletes compiled build products that are not part of the start tree (`*.so`, `*.o`, `build/`, `*.egg-info`, Cython-generated C/C++ files, etc.), then rebuilds it offline in a separate image and runs the hidden tests. No separate patch file is needed.
> - There is no network access at run time.

# Object-oriented short-time Fourier transform (ShortTimeFFT)

Implement the new functionality described below in the provided fixed-version `scipy` source snapshot (working directory `/work`, without git history).

## Background

`scipy.signal.stft/istft` are functional interfaces whose parameter semantics (boundary extension, padding, scaling) are scattered and hard to combine. What is needed is a class whose core state is the window function `win`, the hop `hop` and the sampling frequency `fs`, which explicitly provides the value ranges of the time-slice index p and frequency index q together with the time-frequency coordinates, and which supports the inverse transform (requiring a dual window / canonical dual window) and several one-sided/two-sided FFT modes.

## Required deliverables

1. New module `scipy/signal/_short_time_fft.py`, with `ShortTimeFFT` exported from `scipy.signal` (interface in `INTERFACE.md`): constructor `ShortTimeFFT(win, hop, fs, *, fft_mode="onesided", mfft=None, dual_win=None, scale_to=None, phase_shift=0)`, class methods `from_dual`, `from_window`; `stft`, `stft_detrend`, `istft`, `spectrogram`; properties `win`, `dual_win`, `hop`, `T`, `fs`, `fft_mode`, `mfft`, `scaling`, `m_num`, `m_num_mid`, `phase_shift`, `f_pts`, `onesided_fft`, `f`, `delta_t`, `delta_f`, `p_min`/`p_max(n)`/`p_num(n)`, `k_min`/`k_max(n)`, `lower_border_end`, `upper_border_begin(n)`, `t(n)`, `nearest_k_p`, `extent(n, axes_seq, center_bins)`; `scale_to(scaling)`.
2. Names used directly by the tests: the type aliases `FFT_MODE_TYPE`, `PAD_TYPE`, and `_calc_dual_canonical_window(win, hop)`.
3. Make the necessary compatibility adjustments in `scipy/signal/_spectral_py.py` (e.g. the behavior of `_spectral_helper`/`_triage_segments`, so that the legacy interface and the new class can be cross-checked against each other), and install the new module in `scipy/signal/meson.build`.

The complete target interface (signatures + docstring-level descriptions) is in `INTERFACE.md` in the same directory. Function bodies are omitted; the behavior described by the docstrings is the acceptance criterion. Names marked "internal interface used directly by the tests" must also be provided with the same name and the same signature.

## Allowed scope of changes

- You may add `scipy/signal/_short_time_fft.py` and modify `scipy/signal/__init__.py`, `scipy/signal/_spectral_py.py`, `scipy/signal/meson.build`.
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
