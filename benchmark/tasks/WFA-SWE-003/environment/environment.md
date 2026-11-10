# Environment

Image recipe (identical to grading):

```
Base image: python:3.11-bookworm
System packages: (none)
Python dependencies: numpy<2.2 scipy networkx rustworkx autograd tomlkit appdirs autoray>=0.6.11 cachetools requests typing_extensions packaging diastatic-malt pytest pytest-mock flaky matplotlib pytest-benchmark pytest-xdist
Dependency resolution cutoff: 2025-03-28
```

Build / install (run in the repository root):

```bash
pip install --no-deps --no-build-isolation -e .
```

Self-testing (example; the hidden tests are different):

```bash
python -m pytest -q <your own tests>
```
