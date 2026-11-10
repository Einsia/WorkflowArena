# hidden test command (original private/env/task.sh do_test)
do_test() { python -m pytest -p no:cacheprovider -q qutip/tests/test_bofin_baths.py qutip/tests/test_bofin_solvers.py qutip/tests/test_heom.py; }
