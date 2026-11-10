# Start-tree manifest (MANIFEST)

- Upstream repository: https://github.com/statsmodels/statsmodels (license: BSD-3-Clause)
- Start tree: a source snapshot of a fixed upstream commit, prepared from the pinned upstream revision (check out the fixed commit, initialize submodules, apply the author's kept patch, delete all `.git` history). That commit and the later history contain the answer, so they are not disclosed to the solver.
- Start-tree checksum: `start_tree_sha256 = 39d30f128ca31ebfbf64ed8692deb1ee69ef5f06c8f7c5dfa08fbfd8dc0d48ec` (digest over all files sorted by path, chaining `sha256(path + NUL + sha256(content))`).
- Environment: `env/Dockerfile` (Python dependencies resolved with `uv --exclude-newer <merge date>`).
- The solver receives the generated `/work` directory plus `prompt.zh-CN.md` (the task statement), `INTERFACE.md` and `env/Dockerfile` from this directory.
