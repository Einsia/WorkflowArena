# Build / import commands of this task (from the original private/env/task.sh; paths parameterized).
WS=${WS:-/workspace/qutip}; BLD=${BLD:-/opt/wfs-build}
do_install() { pip install --no-deps --no-build-isolation -e . ; }
do_import() { cd /tmp && python -c "import qutip; print(qutip.__version__)"; }
