# hidden test command (original private/env/task.sh do_test)
do_test() { python -m pytest -p no:cacheprovider -q pennylane/labs/tests/trotter_error; }
