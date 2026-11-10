# 接口说明（仅签名与文档字符串，函数体已省略）。此文件在起点仓库中不存在，需要新建。
"""
Spin-unrestricted G0W0 method based the contour deformation scheme.
The scaling N^4 for valence and N^5 for core states.
GW-CD is particularly recommended for accurate core and high-energy states.

References:
    T. Zhu and G.K.-L. Chan, J. Chem. Theory. Comput. 17, 727-741 (2021)
    J. Chem. Theory Comput. 14, 4856-4869 (2018)
"""

def kernel(gw, load_chk=None):
    """UGWCD kernel.

    Parameters
    ----------
    gw : UGWCD
        instance of UGWCD class
    load_chk : str, optional
        name of chkfile to load

    Returns
    -------
    tuple(bool, ndarray, ndarray)
        conv : bool
            True if converged
        conv_inds : ndarray
            conv_inds[p] = 1 if quasiparticle energy for orbital p is converged
        mo_energy : ndarray
            quasiparticle energies
    """
    ...

def get_sigma_diag(ef, ep, s, p, mo_energy, Lpqa, Lpqb, Lia_a, Lia_b, Wmn_s, freqs, wts, eta):
    """Compute self-energy on real axis using contour deformation.

    Parameters
    ----------
    ef : float
        Fermi level
    ep : float
        quasiparticle energy
    s : int
        spin index
    p : int
        orbital index
    mo_energy : ndarray
        orbital energies
    Lpqa : ndarray
        Lpq for alpha spin
    Lpqb : ndarray
        Lpq for beta spin
    Lia_a : ndarray
        Lpq for alpha spin, occupied-virtual block
    Lia_b : ndarray
        Lpq for beta spin, occupied-virtual block
    Wmn_s : ndarray
        Wmn on imaginary axis for spin s, shape (nw, norbs, nmo)
    freqs : ndarray
        frequencies on imaginary axis
    wts : ndarray
        quadrature weights on imaginary axis
    eta : float
        broadening parameter for poles on real axis

    Returns
    -------
    complex
        self-energy for orbital p and spin s at energy ep
    """
    ...

def get_sigmaR_diag(mo_energy, omega, s, orbp, ef, Lpqa, Lpqb, Lia_a, Lia_b, eta):
    """Compute self-energy for poles inside contour
    (more and more expensive away from Fermi surface).

    Parameters
    ----------
    mo_energy : ndarray
        orbital energies
    omega : float
        quasiparticle energy
    s : int
        spin index
    orbp : int
        orbital index
    ef : float
        Fermi level
    Lpqa : ndarray
        Lpq for alpha spin
    Lpqb : ndarray
        Lpq for beta spin
    Lia_a : ndarray
        Lpq for alpha spin, occupied-virtual block
    Lia_b : ndarray
        Lpq for beta spin, occupied-virtual block
    eta : float
        broadening parameter for poles on real axis

    Returns
    -------
    complex
        self-energy for orbital orbp and spin s at energy omega
    """
    ...

def get_WmnI_diag(gw, orbs, Lpqa, Lpqb, Lia_a, Lia_b, freqs):
    """Compute W_mn(iw) on imaginary axis grids.

    Parameters
    ----------
    gw : UGWCD
        GW object
    orbs : list
        orbital indices
    Lpqa : ndarray
        Lpq for alpha spin
    Lpqb : ndarray
        Lpq for beta spin
    Lia_a : ndarray
        Lpq for alpha spin, occupied-virtual block
    Lia_b : ndarray
        Lpq for beta spin, occupied-virtual block
    freqs : ndarray
        frequencies on imaginary axis

    Returns
    -------
    Wmn : ndarray
        Wmn on imaginary axis, shape (s, Nmo, Norbs, Nw)
    """
    ...

def get_rho_response_R(eia_a, eia_b, omega, Lia_a, Lia_b, eta):
    """Compute density response function in auxiliary basis at poles.

    Parameters
    ----------
    eia_a : ndarray
        Virtual-occupied energy differences for alpha spin
    eia_b : ndarray
        Virtual-occupied energy differences for beta spin
    omega : float
        Frequency
    Lia_a : ndarray
        Lpq for alpha spin, occupied-virtual block
    Lia_b : ndarray
        Lpq for beta spin, occupied-virtual block
    eta : float
        Broadening parameter for poles on real axis

    Returns
    -------
    Pi : ndarray
        Density response function in auxiliary basis at poles
    """
    ...

class UGWCD(UGWAC):

    def __init__(self, mf, frozen=None, auxbasis=None, chkfile=None):
        ...

    def kernel(self):
        """Do one-shot GW calculation using contour deformation."""
        ...
