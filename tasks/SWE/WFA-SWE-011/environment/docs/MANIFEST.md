# Start-tree manifest (MANIFEST)

- Upstream repository: https://github.com/statsmodels/statsmodels (license: BSD-3-Clause)
- Start tree: a source snapshot of a fixed upstream commit, prepared from the pinned upstream revision (check out the fixed commit, initialize submodules, apply the author's kept patch, delete all `.git` history). That commit and the later history contain the answer, so they are not disclosed to the solver.
- Start-tree checksum: `start_tree_sha256 = cef91ded4135fb7024f318c72654d6d0fd1028dc8615d9194a97eef9652ad41c` (digest over all files sorted by path, chaining `sha256(path + NUL + sha256(content))`).
- Environment: `env/Dockerfile` (Python dependencies resolved with `uv --exclude-newer <merge date>`).
- The solver receives the generated `/work` directory plus `prompt.zh-CN.md` (the task statement), `INTERFACE.md` and `env/Dockerfile` from this directory.
