# Environment

Image recipe (identical to grading):

```
Base image: python:3.9-bookworm
System packages: (none)
Python dependencies: numpy<1.20 scipy<1.8 cython<3 setuptools<60 wheel packaging pytest pytest-rerunfailures
Dependency resolution cutoff: 2021-11-23
```

Build / install (run in the repository root):

```bash
pip install --no-deps --no-build-isolation -e .
```

Self-testing (example; the hidden tests are different):

```bash
python -m pytest -q <your own tests>
```
