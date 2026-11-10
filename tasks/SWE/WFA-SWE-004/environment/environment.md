# Environment

Image recipe (identical to grading):

```
Base image: python:3.12-bookworm
System packages: cmake libopenblas-dev
Python dependencies: numpy scipy h5py pytest pytest-xdist pytest-timeout
Dependency resolution cutoff: 2026-07-14
```

Build / install (works offline; the same function is used by the grader):

```bash
bash -c '. /opt/wfs/build.sh && do_install && do_import'
```

`do_install` runs in `/workspace/pyscf/pyscf/lib`: it copies the pre-fetched third-party libraries from `/cache/deps` into `pyscf/lib/deps`, configures with `cmake -B build -S . -DBUILD_LIBCINT=0 -DBUILD_LIBXC=0 -DBUILD_XCFUN=0 -DCMAKE_BUILD_TYPE=Release` and builds with `cmake --build build -j 24`. Do not run a plain `cmake -B build -S .` without the `-DBUILD_*=0` flags: it tries to download libcint/libxc/xcfun, which fails without network. `PYTHONPATH=/workspace/pyscf` is set in the image (no pip install).

Self-testing (example; the hidden tests are different):

```bash
python -m pytest -q <your own tests>
```
