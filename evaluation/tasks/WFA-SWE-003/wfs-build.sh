# Build / import commands of this task (from the original private/env/task.sh; paths parameterized).
WS=${WS:-/workspace/pennylane}; BLD=${BLD:-/opt/wfs-build}
do_install() { pip install --no-deps --no-build-isolation -e . ; }
do_import() { python -c "import pennylane as qml, pennylane.labs; print(qml.__version__)"; }
