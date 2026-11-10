# Build / import commands of this task (from the original private/env/task.sh; paths parameterized).
WS=${WS:-/workspace/pyscf}; BLD=${BLD:-/opt/wfs-build}
do_install() {
  set -e; cd $WS/pyscf/lib
  if [ -d /cache/deps ]; then cp -a /cache/deps deps; FL="-DBUILD_LIBCINT=0 -DBUILD_LIBXC=0 -DBUILD_XCFUN=0"; else FL=""; fi
  cmake -B build -S . $FL -DCMAKE_BUILD_TYPE=Release
  cmake --build build -j 24
  [ -d /cache/deps ] || cp -a deps /cache/deps
}
do_import() { cd /tmp && PYTHONPATH=$WS python -c "import pyscf, pyscf.lib, pyscf.dft; print(pyscf.__version__)"; }
