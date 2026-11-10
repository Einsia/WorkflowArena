# 接口说明（仅签名与文档字符串，函数体已省略）。此文件在起点仓库中不存在，需要新建。
"""
Spin-restricted G0W0 method based on the fully analytic scheme.
This implementation has N^6 scaling, and is accurate for all states.

Reference:
    J. Chem. Theory Comput. 9, 1, 232-246 (2013)
"""

def kernel(gw):
    ...

def diagonalize_phrpa(nocc, mo_energy, Lpq, RPAE=False):
    """Diagonalize particle-hole RPA matrix.
    The phRPA equation is solved for the response function for the screening interaction,
    which is defined in equation 66-68 in doi.org/10.1021/ct300648t
    The phRPA equation is reformulated as (A-B)(A+B)|X+Y>= \\omega^2|X+Y>, which is equation 15 in 10.1063/1.477483
    RPAE equations are defined as equation 2 and 3 in 10.1103/PhysRevA.85.042507

    Parameters
    ----------
    nocc : int
        the number of occupied orbitals
    mo_energy : double 1d array
        orbital energy
    Lpq : double 3d array
        density-fitting matrix in the MO space
    RPAE : bool, optional
        add exchange in response, by default False

    Returns
    -------
    w : double 1d array
        excitation energy
    v : double 2d array
        X+Y eigenvector
    """
    ...

def get_transition_density(nocc, xpy, Lpq):
    """Calculate the transition density.
    Equation.85 in doi/abs/10.1021/ct300648t.

    Parameters
    ----------
    nocc : int
        the number of occupied orbitals
    xpy : double 2d array
        X+Y eigenvector
    Lpq : double 3d array
        density-fitting matrix in the MO space

    Returns
    -------
    rho: double 3d array
        transition density
    """
    ...

def get_sigma(nocc, mo_energy, mo_energy_prev, exci, rho, eta=1e-05, fullsigma=False, mode='b'):
    """Get the real part of the GW correlation self-energy.
    Equation 83 in doi.org/10.1021/ct300648t
    mode 'a' and 'b' correspond to equation 10 and 11 in doi.org/10.1103/PhysRevB.76.165106

    Parameters
    ----------
    nocc : int
        the number of occupied orbitals
    mo_energy : double 1d array
        orbital energy
    mo_energy_prev : double 1d array
        orbital energy in previous iteration
    exci : double 1d array
        phRPA excitation energy
    rho : double 3d array
        transition density
    eta : double, optional
        broadening parameter, by default 1.0e-5
    fullsigma : bool, optional
        calculate off-diagonal elements, by default False
    mode : str, optional
        mode for off-diagonal elements, by default "b"

    Returns
    -------
    sigma : double 2d array
        real part of the GW static correlation self-energy
    """
    ...

def get_sigma_derivative(nocc, mo_energy, mo_energy_prev, exci, rho, eta=1e-05):
    """Get the first-order derivative of the self-energy to the frequency.
    Equation.84 in doi.org/10.1021/ct300648t

    Parameters
    ----------
    nocc : int
        the number of occupied orbitals
    mo_energy : double 1d array
        orbital energy
    mo_energy_prev : double 1d array
        orbital energy in previous iteration
    exci : double 1d array
        phRPA excitation energy
    rho : double 3d array
        transition density
    eta : double, optional
        broadening parameter, by default 1.0e-5

    Returns
    -------
    derivative : double 1d array
        first-order derivative of the correlation self-energy to the frequency
    """
    ...

def make_gf(gw, omega, eta, fullsigma=True, mode='linear'):
    """Get exact dynamical Green's function and self-energy.
    Dynamical self-energy is evaluated as equation 78 in doi.org/10.1021/ct300648t

    Two modes for solving Dyson equation
    "dyson" for using inverse Dyson equation.
    "linear" for G = G0 + G0 Sigma G0, as equation 16 in doi.org/10.1021/acs.jctc.0c01264

    Parameters
    ----------
    gw : GWExact
        gw object, provides attributes: nocc, nmo, _scf.mo_energy, exci, rho, vk, vxc
    omega : double or complex array
        frequency grids
    eta : double
        broadening parameter
    fullsigma : bool, optional
        calculate off-diagonal elements, by default True
    mode : str, optional
        mode for Dyson equation, 'linear' or 'dyson', by default 'linear'

    Returns
    -------
    gf : complex 3d array
        GW Green's function
    gf0 : complex 3d array
        non-interacting Green's function
    sigma : complex 3d array
        self-energy
    """
    ...

def make_diag_dos(gw, omega, eta):
    """Get density of states using diagonal self-energy.
    Equation 7 in doi.org/10.1021/acs.jctc.2c00617

    Parameters
    ----------
    gw : GWExact
        gw object, provides attributes: nocc, nmo, _scf.mo_energy, exci, rho, vk, vxc
    omega : complex 1d array
        frequency grids
    eta : double
        broadening parameter

    Returns
    -------
    dos : double 2d array
        orbital-resolved density of states
    """
    ...

class GWExactDF(GWAC):

    def __init__(self, mf, auxbasis=None):
        ...

    def dump_flags(self, verbose=None):
        ...

    def kernel(self):
        ...
    make_gf = make_gf
    make_diag_dos = make_diag_dos

    def make_rdm1(self, nw=60, mode='linear', ao_repr=False):
        """Get GW one-particle density matrix.
        rdm1 = G(it=0) = \\int dw G(iw)

        Parameters
        ----------
        nw : int, optional
            number for imaginary frequency grids for integration, by default 60
        mode : str, optional
            mode for Dyson equation, by default 'linear'
        ao_repr : bool, optional
            return density matrix in AO, by default False

        Returns
        -------
        rdm1 : double ndarray
            one-particle density matrix
        """
        ...

    def energy_tot(self, nw=60):
        """Calculate GW total energy using Galitskii-Migdal formula.
        V. M. Galitskii and A. B. Migdal, Zh. E ksp. Teor. Fiz. 34, 139~1958! @Sov. Phys. JETP 139, 96 ~1958!#
        Working equation: equation A5 in Phys. Rev. B 88, 075105

        Parameters
        ----------
        nw : int, optional
            number for imaginary frequency grids for integration, by default 60

        Returns
        -------
        e_tot : double
            GW total energy
        e_hf : double
            HF total energy
        e_c : double
            GW correlation energy
        """
        ...
