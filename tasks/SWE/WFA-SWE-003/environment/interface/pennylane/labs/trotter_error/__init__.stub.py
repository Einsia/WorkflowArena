# 接口说明（仅签名与文档字符串，函数体已省略）。此文件在起点仓库中不存在，需要新建。
"""Module containing functionality for computing Trotter error.

.. warning::

    This module is experimental. Frequent changes will occur,
    with no guarantees of stability or backwards compatibility.

.. currentmodule:: pennylane.labs.trotter_error

Trotter Base Classes
~~~~~~~~~~~~~~~~~~~~
Abstract classes specifying the methods needed for implementing fragments and states in the Trotter error workflow.

.. autosummary::
    :toctree: api

    ~AbstractState
    ~Fragment

Fragment Classes
~~~~~~~~~~~~~~~~
Classes representing fragments of different types of Hamiltonians.

.. autosummary::
    :toctree: api

    ~GenericFragment
    ~RealspaceMatrix
    ~RealspaceSum

Realspace Hamiltonian Classes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Classes used to store representations of realspace Hamiltonians.

.. autosummary::
    :toctree: api

    ~RealspaceCoeffs
    ~RealspaceOperator

Fragment Functions
~~~~~~~~~~~~~~~~~~
Functions used to retrieve fragments of various Hamiltonians.

.. autosummary::
    :toctree: api

    ~generic_fragments
    ~vibrational_fragments
    ~vibronic_fragments

Harmonic Oscillator Classes
~~~~~~~~~~~~~~~~~~~~~~~~~~~
Classes used to construct the representation of harmonic oscillator states.

.. autosummary::
    :toctree: api

    ~HOState
    ~VibronicHO

Error Estimation Functions
~~~~~~~~~~~~~~~~~~~~~~~~~~
Functions for computing Trotter error estimates.

.. autosummary::
    :toctree: api

    ~perturbation_error
    ~trotter_error
"""
