# 接口说明（仅签名与文档字符串，函数体已省略）。此文件在起点仓库中已存在；以下只列出需要新增或修改的类/函数（其余已有内容保持不变）。
"""
Spin-restricted G0W0 method based the contour deformation scheme.
The scaling N^4 for valence and N^5 for core states.
GW-CD is particularly recommended for accurate core and high-energy states.

References:
    T. Zhu and G.K.-L. Chan, J. Chem. Theory. Comput. 17, 727-741 (2021)
    J. Chem. Theory Comput. 14, 4856-4869 (2018)
"""

def kernel(gw, load_chk=None):
    """GWCD kernel.

    Parameters
    ----------
    gw : GWCD
        instance of GWCD class
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

def get_sigma_diag(ef, ep, p, mo_energy, Lpq, Lia, Wmn, freqs, wts, eta):
    """Compute self-energy on real axis using contour deformation.

    Parameters
    ----------
    ef : double
        Fermi level
    ep : double
        frequency at which to evaluate self-energy
    p : int
        orbital index for which to compute self-energy
    mo_energy : double 1d array
        MO energies
    Lpq : double 3d array
        three-center density-fitting matrix in MO space
    Lia : double 3d array
        three-center density-fitting matrix in MO space, O-V block
    Wmn : double 2d array
        Wmn on imaginary axis, shape (nw, nmo)
    freqs : double 1d array
        position of imaginary frequency grids used for integration
    wts : double 1d array
        weights of imaginary frequency grids used for integration
    eta : double
        smearing parameter for poles

    Returns
    -------
    complex
        self-energy for orbital p at frequency ep
    """
    ...

def get_sigmaR_diag(mo_energy, omega, orbp, ef, Lpq, Lia, eta):
    """Compute self-energy for poles inside contour
    (more and more expensive away from Fermi surface).

    Parameters
    ----------
    mo_energy : double 1d array
        MO energies
    omega : double
        frequency at which to evaluate self-energy
    orbp : int
        orbital index for which to compute self-energy
    ef : double
        Fermi level
    Lpq : double 3d array
        three-center density-fitting matrix in MO space
    Lia : double 3d array
        three-center density-fitting matrix in MO space, O-V block
    eta : double
        smearing parameter for poles

    Returns
    -------
    complex
        self-energy for orbital orbp at frequency omega from poles inside contour
    """
    ...

def get_WmnI_diag(gw, orbs, Lpq, Lia, quad_freqs, mo_energy):
    """Calculate Wmn on imaginary axis.

    Parameters
    ----------
    gw : GWCD
        GWCD object
    orbs : list
        list of orbital indexes
    Lpq : double 3d array
        three-center density-fitting matrix in MO space
    Lia : double 3d array
        three-center density-fitting matrix in MO space, O-V block
    quad_freqs : double 1d array
        position of imaginary frequency grids used for integration
    mo_energy : double 1d array
        MO energies

    Returns
    -------
    complex 3d array
        Wmn on imaginary axis, shape (nw, norbs, nmo)
    """
    ...

def get_rho_response_R(eia, omega, Lia, eta):
    """
    Compute density response function in auxiliary basis at poles.

    Parameters
    ----------
    eia : double 2d array
        eia[i,a] = mo_energy[i] - mo_energy[a], where i is occupied and a is virtual
    omega : double
        frequency at which to evaluate response function
    Lia : double 3d array
        three-center density-fitting matrix in MO space, O-V block
    eta : double
        smearing parameter for poles

    Returns
    -------
    complex 2d array
        density response function in auxiliary basis at poles
    """
    ...

class GWCD(GWAC):

    def __init__(self, mf, frozen=None, auxbasis=None, chkfile=None):
        ...

    def kernel(self):
        """Do one-shot GW calculation using contour deformation."""
        ...
