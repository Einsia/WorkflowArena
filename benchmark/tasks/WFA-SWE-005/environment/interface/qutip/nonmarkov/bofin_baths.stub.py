# 接口说明（仅签名与文档字符串，函数体已省略）。此文件在起点仓库中不存在，需要新建。
"""
This module provides utilities for describing baths when using the
HEOM (hierarchy equations of motion) to model system-bath interactions.

See the ``qutip.nonmarkov.bofin_solvers`` module for the associated solver.

"""

class BathExponent:
    """
    Represents a single exponent (naively, an excitation mode) within the
    decomposition of the correlation functions of a bath.

    Parameters
    ----------
    type : {"R", "I", "RI", "+", "-"} or BathExponent.ExponentType
        The type of bath exponent.

        "R" and "I" are bosonic bath exponents that appear in the real and
        imaginary parts of the correlation expansion.

        "RI" is combined bosonic bath exponent that appears in both the real
        and imaginary parts of the correlation expansion. The combined exponent
        has a single ``vk``. The ``ck`` is the coefficient in the real
        expansion and ``ck2`` is the coefficient in the imaginary expansion.

        "+" and "-" are fermionic bath exponents. These fermionic bath
        exponents must specify ``sigma_bar_k_offset`` which specifies
        the amount to add to ``k`` (the exponent index within the bath of this
        exponent) to determine the ``k`` of the corresponding exponent with
        the opposite sign (i.e. "-" or "+").

    dim : int or None
        The dimension (i.e. maximum number of excitations for this exponent).
        Usually ``2`` for fermionic exponents or ``None`` (i.e. unlimited) for
        bosonic exponents.

    Q : Qobj
        The coupling operator for this excitation mode.

    vk : complex
        The frequency of the exponent of the excitation term.

    ck : complex
        The coefficient of the excitation term.

    ck2 : optional, complex
        For exponents of type "RI" this is the coefficient of the term in the
        imaginary expansion (and ``ck`` is the coefficient in the real
        expansion).

    sigma_bar_k_offset : optional, int
        For exponents of type "+" this gives the offset (within the list of
        exponents within the bath) of the corresponding "-" bath exponent.
        For exponents of type "-" it gives the offset of the corresponding
        "+" exponent.

    tag : optional, str, tuple or any other object
        A label for the exponent (often the name of the bath). It
        defaults to None.

    Attributes
    ----------

    All of the parameters are available as attributes.
    """
    types = enum.Enum('ExponentType', ['R', 'I', 'RI', '+', '-'])

    def __init__(self, type, dim, Q, ck, vk, ck2=None, sigma_bar_k_offset=None, tag=None):
        ...

class Bath:
    """
    Represents a list of bath expansion exponents.

    Parameters
    ----------
    exponents : list of BathExponent
        The exponents of the correlation function describing the bath.

    Attributes
    ----------

    All of the parameters are available as attributes.
    """

    def __init__(self, exponents):
        ...

class BosonicBath(Bath):
    """
    A helper class for constructing a bosonic bath from the expansion
    coefficients and frequencies for the real and imaginary parts of
    the bath correlation function.

    If the correlation functions ``C(t)`` is split into real and imaginary
    parts::

        C(t) = C_real(t) + i * C_imag(t)

    then::

        C_real(t) = sum(ck_real * exp(- vk_real * t))
        C_imag(t) = sum(ck_imag * exp(- vk_imag * t))

    Defines the coefficients ``ck`` and the frequencies ``vk``.

    Note that the ``ck`` and ``vk`` may be complex, even through ``C_real(t)``
    and ``C_imag(t)`` (i.e. the sum) is real.

    Parameters
    ----------
    Q : Qobj
        The coupling operator for the bath.

    ck_real : list of complex
        The coefficients of the expansion terms for the real part of the
        correlation function. The corresponding frequencies are passed as
        vk_real.

    vk_real : list of complex
        The frequencies (exponents) of the expansion terms for the real part of
        the correlation function. The corresponding ceofficients are passed as
        ck_real.

    ck_imag : list of complex
        The coefficients of the expansion terms in the imaginary part of the
        correlation function. The corresponding frequencies are passed as
        vk_imag.

    vk_imag : list of complex
        The frequencies (exponents) of the expansion terms for the imaginary
        part of the correlation function. The corresponding ceofficients are
        passed as ck_imag.

    combine : bool, default True
        Whether to combine exponents with the same frequency (and coupling
        operator). See :meth:`combine` for details.

    tag : optional, str, tuple or any other object
        A label for the bath exponents (for example, the name of the
        bath). It defaults to None but can be set to help identify which
        bath an exponent is from.
    """

    def __init__(self, Q, ck_real, vk_real, ck_imag, vk_imag, combine=True, tag=None):
        ...

    @classmethod
    def combine(cls, exponents, rtol=1e-05, atol=1e-07):
        """
        Group bosonic exponents with the same frequency and return a
        single exponent for each frequency present.

        Exponents with the same frequency are only combined if they share the
        same coupling operator ``.Q``.

        Note that combined exponents take their tag from the first
        exponent in the group being combined (i.e. the one that occurs first
        in the given exponents list).

        Parameters
        ----------
        exponents : list of BathExponent
            The list of exponents to combine.

        rtol : float, default 1e-5
            The relative tolerance to use to when comparing frequencies and
            coupling operators.

        atol : float, default 1e-7
            The absolute tolerance to use to when comparing frequencies and
            coupling operators.

        Returns
        -------
        list of BathExponent
            The new reduced list of exponents.
        """
        ...

class DrudeLorentzBath(BosonicBath):
    """
    A helper class for constructing a Drude-Lorentz bosonic bath from the
    bath parameters (see parameters below).

    Parameters
    ----------
    Q : Qobj
        Operator describing the coupling between system and bath.

    lam : float
        Coupling strength.

    T : float
        Bath temperature.

    Nk : int
        Number of exponential terms used to approximate the bath correlation
        functions.

    gamma : float
        Bath spectral density cutoff frequency.

    terminator : bool, default False
        Whether to calculate the Matsubara terminator for the bath. If
        true, the calculated terminator and the calculated approximation
        discrepancy are provided via the ``.terminator`` and ``.delta``
        attributes, respectively. Otherwise, ``.terminator`` and ``.delta`` are
        both set to ``None``. The terminator is a Liouvillian term, so it's
        dimensions are those of a superoperator of ``Q``.

    combine : bool, default True
        Whether to combine exponents with the same frequency (and coupling
        operator). See :meth:`BosonicBath.combine` for details.

    tag : optional, str, tuple or any other object
        A label for the bath exponents (for example, the name of the
        bath). It defaults to None but can be set to help identify which
        bath an exponent is from.

    Attributes
    ----------
    terminator : Qobj
        The Matsubara terminator -- i.e. a liouvillian term representing the
        contribution to the system-bath dynamics of all exponential expansion
        terms beyond Nk. It should be used by adding it to the system
        liouvillian (i.e. ``liouvillian(H_sys)``).

    delta : float
        The approximation discrepancy. That is, the difference between the true
        correlation function of the Drude-Lorentz bath and the sum of the
        ``Nk`` exponential terms is approximately ``2 * delta * dirac(t)``,
        where ``dirac(t)`` denotes the Dirac delta function.
    """

    def __init__(self, Q, lam, T, Nk, gamma, terminator=False, combine=True, tag=None):
        ...

class DrudeLorentzPadeBath(BosonicBath):
    """
    A helper class for constructing a Padé expansion for a Drude-Lorentz
    bosonic bath from the bath parameters (see parameters below).

    A Padé approximant is a sum-over-poles expansion (
    see https://en.wikipedia.org/wiki/Pad%C3%A9_approximant).

    The application of the Padé method to spectrum decompoisitions is described
    in "Padé spectrum decompositions of quantum distribution functions and
    optimal hierarchical equations of motion construction for quantum open
    systems" [1].

    The implementation here follows the approach in the paper.

    [1] J. Chem. Phys. 134, 244106 (2011); https://doi.org/10.1063/1.3602466

    This is an alternative to the :class:`DrudeLorentzBath` which constructs
    a simpler exponential expansion.

    Parameters
    ----------
    Q : Qobj
        Operator describing the coupling between system and bath.

    lam : float
        Coupling strength.

    T : float
        Bath temperature.

    Nk : int
        Number of Padé exponentials terms used to approximate the bath
        correlation functions.

    gamma : float
        Bath spectral density cutoff frequency.

    terminator : bool, default False
        Whether to calculate the Padé terminator for the bath. If true, the
        calculated terminator and the calculated approximation discrepancy are
        provided via the ``.terminator`` and ``.delta`` attributes,
        respectively. Otherwise, ``.terminator`` and ``.delta`` are both set to
        ``None``. The terminator is a Liouvillian term, so it's dimensions are
        those of a superoperator of ``Q``.

    combine : bool, default True
        Whether to combine exponents with the same frequency (and coupling
        operator). See :meth:`BosonicBath.combine` for details.

    tag : optional, str, tuple or any other object
        A label for the bath exponents (for example, the name of the
        bath). It defaults to None but can be set to help identify which
        bath an exponent is from.

    Attributes
    ----------
    terminator : Qobj
        The Padé terminator -- i.e. a liouvillian term representing the
        contribution to the system-bath dynamics of all exponential expansion
        terms beyond Nk. It should be used by adding it to the system
        liouvillian (i.e. ``liouvillian(H_sys)``).

    delta : float
        The approximation discrepancy. That is, the difference between the true
        correlation function of the Drude bath and the correlation function
        represented by this object is approximately ``2 delta * dirac(t)``,
        where ``dirac(t)`` denotes the Dirac delta function.
    """

    def __init__(self, Q, lam, T, Nk, gamma, terminator=False, combine=True, tag=None):
        ...

class UnderDampedBath(BosonicBath):
    """
    A helper class for constructing an under-damped bosonic bath from the
    bath parameters (see parameters below).

    Parameters
    ----------
    Q : Qobj
        Operator describing the coupling between system and bath.

    lam : float
        Coupling strength.

    T : float
        Bath temperature.

    Nk : int
        Number of exponential terms used to approximate the bath correlation
        functions.

    gamma : float
        Bath spectral density cutoff frequency.

    w0 : float
        Bath spectral density resonance frequency.

    combine : bool, default True
        Whether to combine exponents with the same frequency (and coupling
        operator). See :meth:`BosonicBath.combine` for details.

    tag : optional, str, tuple or any other object
        A label for the bath exponents (for example, the name of the
        bath). It defaults to None but can be set to help identify which
        bath an exponent is from.
    """

    def __init__(self, Q, lam, T, Nk, gamma, w0, combine=True, tag=None):
        ...

class FermionicBath(Bath):
    """
    A helper class for constructing a fermionic bath from the expansion
    coefficients and frequencies for the ``+`` and ``-`` modes of
    the bath correlation function.

    There must be the same number of ``+`` and ``-`` modes and their
    coefficients must be specified in the same order so that ``ck_plus[i],
    vk_plus[i]`` are the plus coefficient and frequency corresponding
    to the minus mode ``ck_minus[i], vk_minus[i]``.

    In the fermionic case the order in which excitations are created or
    destroyed is important, resulting in two different correlation functions
    labelled ``C_plus(t)`` and ``C_plus(t)``::

        C_plus(t) = sum(ck_plus * exp(- vk_plus * t))
        C_minus(t) = sum(ck_minus * exp(- vk_minus * t))

    where the expansions above define the coeffiients ``ck`` and the
    frequencies ``vk``.

    Parameters
    ----------
    Q : Qobj
        The coupling operator for the bath.

    ck_plus : list of complex
        The coefficients of the expansion terms for the ``+`` part of the
        correlation function. The corresponding frequencies are passed as
        vk_plus.

    vk_plus : list of complex
        The frequencies (exponents) of the expansion terms for the ``+`` part
        of the correlation function. The corresponding ceofficients are passed
        as ck_plus.

    ck_minus : list of complex
        The coefficients of the expansion terms for the ``-`` part of the
        correlation function. The corresponding frequencies are passed as
        vk_minus.

    vk_minus : list of complex
        The frequencies (exponents) of the expansion terms for the ``-`` part
        of the correlation function. The corresponding ceofficients are passed
        as ck_minus.

    tag : optional, str, tuple or any other object
        A label for the bath exponents (for example, the name of the
        bath). It defaults to None but can be set to help identify which
        bath an exponent is from.
    """

    def __init__(self, Q, ck_plus, vk_plus, ck_minus, vk_minus, tag=None):
        ...
