# 接口说明（仅签名与文档字符串，函数体已省略）。此文件在起点仓库中已存在；以下只列出需要新增或修改的类/函数（其余已有内容保持不变）。
"""
This module provides solvers for system-bath evoluation using the
HEOM (hierarchy equations of motion).

See https://en.wikipedia.org/wiki/Hierarchical_equations_of_motion for a very
basic introduction to the technique.


For backwards compatibility with QuTiP 4.6 and below, a new version of
HSolverDL (the Drude-Lorentz specific HEOM solver) is provided. It is
implemented on top of the new HEOMSolver but should largely be a drop-in
replacement for the old HSolverDL.

An exact copy of the QuTiP 4.6 HSolverDL is provided in
``qutip.nonmarkov.dlheom_solver`` for cases where the functionality of the
older solver is required. The older solver will be completely removed in
QuTiP 5.
"""
__all__ = ['BathExponent', 'Bath', 'BosonicBath', 'DrudeLorentzBath', 'DrudeLorentzPadeBath', 'UnderDampedBath', 'FermionicBath', 'HEOMSolver', 'HSolverDL']
