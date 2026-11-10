# 接口说明（仅签名与文档字符串，函数体已省略）。此文件在起点仓库中不存在，需要新建。
"""
This module provides solvers for system-bath evoluation using the
HEOM (hierarchy equations of motion).

See https://en.wikipedia.org/wiki/Hierarchical_equations_of_motion for a very
basic introduction to the technique.

"""

class HierarchyADOs:
    """
    A description of ADOs (auxilliary density operators) with the
    hierarchical equations of motion.

    The list of ADOs is constructed from a list of bath exponents
    (corresponding to one or more baths). Each ADO is referred to by a label
    that lists the number of "excitations" of each bath exponent. The
    level of a label within the hierarchy is the sum of the "excitations"
    within the label.

    For example the label ``(0, 0, ..., 0)`` represents the density matrix
    of the system being solved and is the only 0th level label.

    The labels with a single 1, i.e. ``(1, 0, ..., 0)``, ``(0, 1, 0, ... 0)``,
    etc. are the 1st level labels.

    The second level labels all have either two 1s or a single 2, and so on
    for the third and higher levels of the hierarchy.

    Parameters
    ----------
    exponents : list of BathExponent
        The exponents of the correlation function describing the bath or
        baths.

    max_depth : int
        The maximum depth of the hierarchy (i.e. the maximum sum of
        "excitations" in the hierarchy ADO labels or maximum ADO level).

    Attributes
    ----------
    exponents : list of BathExponent
        The exponents of the correlation function describing the bath or
        baths.

    max_depth : int
        The maximum depth of the hierarchy (i.e. the maximum sum of
        "excitations" in the hierarchy ADO labels).

    dims : list of int
        The dimensions of each exponent within the bath(s).

    vk : list of complex
        The frequency of each exponent within the bath(s).

    ck : list of complex
        The coefficient of each exponent within the bath(s).

    ck2: list of complex
        For exponents of type "RI", the coefficient of the exponent within
        the imaginary expansion. For other exponent types, the entry is None.

    sigma_bar_k_offset: list of int
        For exponents of type "+" or "-" the offset within the list of modes
        of the corresponding "-" or "+" exponent. For other exponent types,
        the entry is None.

    labels: list of tuples
        A list of the ADO labels within the hierarchy.
    """

    def __init__(self, exponents, max_depth):
        ...

    def idx(self, label):
        """
        Return the index of the ADO label within the list of labels,
        i.e. within ``self.labels``.

        Parameters
        ----------
        label : tuple
            The label to look up.

        Returns
        -------
        int
            The index of the label within the list of ADO labels.
        """
        ...

    def next(self, label, k):
        """
        Return the ADO label with one more excitation in the k'th exponent
        dimension or ``None`` if adding the excitation would exceed the
        dimension or maximum depth of the hierarchy.

        Parameters
        ----------
        label : tuple
            The ADO label to add an excitation to.
        k : int
            The exponent to add the excitation to.

        Returns
        -------
        tuple or None
            The next label.
        """
        ...

    def prev(self, label, k):
        """
        Return the ADO label with one fewer excitation in the k'th
        exponent dimension or ``None`` if the label has no exciations in the
        k'th exponent.

        Parameters
        ----------
        label : tuple
            The ADO label to remove the excitation from.
        k : int
            The exponent to remove the excitation from.

        Returns
        -------
        tuple or None
            The previous label.
        """
        ...

    def exps(self, label):
        """
        Converts an ADO label into a tuple of exponents, with one exponent
        for each "excitation" within the label.

        The number of exponents returned is always equal to the level of the
        label within the hierarchy (i.e. the sum of the indices within the
        label).

        Parameters
        ----------
        label : tuple
            The ADO label to convert to a list of exponents.

        Returns
        -------
        tuple of BathExponent
            A tuple of BathExponents.

        Examples
        --------

        ``ados.exps((1, 0, 0))`` would return ``[ados.exponents[0]]``

        ``ados.exps((2, 0, 0))`` would return
        ``[ados.exponents[0], ados.exponents[0]]``.

        ``ados.exps((1, 2, 1))`` would return
        ``[ados.exponents[0], ados.exponents[1], ados.exponents[1],            ados.exponents[2]]``.
        """
        ...

    def filter(self, level=None, tags=None, dims=None, types=None):
        """
        Return a list of ADO labels for ADOs whose "excitations"
        match the given patterns.

        Each of the filter parameters (tags, dims, types) may be either
        unspecified (None) or a list. Unspecified parameters are excluded
        from the filtering.

        All specified filter parameters must be lists of the same length.
        Each position in the lists describes a particular excitation and
        any exponent that matches the filters may supply that excitation.
        The level of all labels returned is thus equal to the length of
        the filter parameter lists.

        Within a filter parameter list, items that are None represent
        wildcards and match any value of that exponent attribute

        Parameters
        ----------
        level : int
            The hierarchy depth to return ADOs from.

        tags : list of object or None
            Filter parameter that matches the ``.tag`` attribute of
            exponents.

        dims : list of int
            Filter parameter that matches the ``.dim`` attribute of
            exponents.

        types : list of BathExponent types or list of str
            Filter parameter that matches the ``.type`` attribute
            of exponents. Types may be supplied by name (e.g. "R", "I", "+")
            instead of by the actual type (e.g. ``BathExponent.types.R``).

        Returns
        -------
        list of tuple
            The ADO label for each ADO whose exponent excitations
            (i.e. label) match the given filters or level.
        """
        ...

class HierarchyADOsState:
    """
    Provides convenient access to the full hierarchy ADO state at a particular
    point in time, ``t``.

    Parameters
    ----------
    rho : :class:`Qobj`
        The current state of the system (i.e. the 0th component of the
        hierarchy).
    ados : :class:`HierarchyADOs`
        The description of the hierarchy.
    ado_state : numpy.array
        The full state of the hierarchy.

    Attributes
    ----------
    rho : Qobj
        The system state.

    In addition, all of the attributes of the hierarchy description,
    i.e. ``HierarchyADOs``, are provided directly on this class for
    convenience. E.g. one can access ``.labels``, or ``.exponents`` or
    call ``.idx(label)`` directly.

    See :class:`HierarchyADOs` for a full list of the available attributes
    and methods.
    """

    def __init__(self, rho, ados, ado_state):
        ...

    def __getattr__(self, name):
        ...

    def extract(self, idx_or_label):
        """
        Extract a Qobj representing specified ADO from a full representation of
        the ADO states.

        Parameters
        ----------
        idx : int or label
            The index of the ADO to extract. If an ADO label, e.g.
            ``(0, 1, 0, ...)`` is supplied instead, then the ADO
            is extracted by label instead.

        Returns
        -------
        Qobj
            A :obj:`Qobj` representing the state of the specified ADO.
        """
        ...

class HEOMSolver:
    """
    HEOM solver that supports multiple baths.

    The baths must be all either bosonic or fermionic baths.

    Parameters
    ----------
    H_sys : QObj, QobjEvo or a list
        The system Hamiltonian or Liouvillian specified as either a
        :obj:`Qobj`, a :obj:`QobjEvo`, or a list of elements that may
        be converted to a :obj:`ObjEvo`.

    bath : Bath or list of Bath
        A :obj:`Bath` containing the exponents of the expansion of the
        bath correlation funcion and their associated coefficients
        and coupling operators, or a list of baths.

        If multiple baths are given, they must all be either fermionic
        or bosonic baths.

    max_depth : int
        The maximum depth of the heirarchy (i.e. the maximum number of bath
        exponent "excitations" to retain).

    options : :class:`qutip.solver.Options`
        Generic solver options. If set to None the default options will be
        used.

    progress_bar : None, True or :class:`BaseProgressBar`
        Optional instance of BaseProgressBar, or a subclass thereof, for
        showing the progress of the solver. If True, an instance of
        :class:`TextProgressBar` is used instead.

    Attributes
    ----------
    ados : :obj:`HierarchyADOs`
        The description of the hierarchy constructed from the given bath
        and maximum depth.
    """

    def __init__(self, H_sys, bath, max_depth, options=None, progress_bar=None):
        ...

    def steady_state(self, use_mkl=True, mkl_max_iter_refine=100, mkl_weighted_matching=False):
        """
        Compute the steady state of the system.

        Parameters
        ----------
        use_mkl : bool, default=False
            Whether to use mkl or not. If mkl is not installed or if
            this is false, use the scipy splu solver instead.

        mkl_max_iter_refine : int
            Specifies the the maximum number of iterative refinement steps that
            the MKL PARDISO solver performs.

            For a complete description, see iparm(8) in
            http://cali2.unilim.fr/intel-xe/mkl/mklman/GUID-264E311E-ACED-4D56-AC31-E9D3B11D1CBF.htm.

        mkl_weighted_matching : bool
            MKL PARDISO can use a maximum weighted matching algorithm to
            permute large elements close the diagonal. This strategy adds an
            additional level of reliability to the factorization methods.

            For a complete description, see iparm(13) in
            http://cali2.unilim.fr/intel-xe/mkl/mklman/GUID-264E311E-ACED-4D56-AC31-E9D3B11D1CBF.htm.

        Returns
        -------
        steady_state : Qobj
            The steady state density matrix of the system.

        steady_ados : :class:`HierarchyADOsState`
            The steady state of the full ADO hierarchy. A particular ADO may be
            extracted from the full state by calling :meth:`.extract`.
        """
        ...

    def run(self, rho0, tlist, e_ops=None, ado_init=False, ado_return=False):
        """
        Solve for the time evolution of the system.

        Parameters
        ----------
        rho0 : Qobj or numpy.array
            Initial state (density matrix) of the system
            if ``full_init`` is ``False``.
            If ``full_init`` is ``True``, then ``rho0`` should be a numpy array
            of the initial state and the initial state of all ADOs. Usually
            the state of the ADOs would be determine from a previous call
            to ``.run(..., ado_return=True)``.

        tlist : list
            An ordered list of times at which to return the value of the state.

        e_ops : Qobj / callable / list / dict / None, optional
            A list or dictionary of operators as `Qobj` and/or callable
            functions (they can be mixed) or a single operator or callable
            function. For an operator ``op``, the result will be computed
            using ``(state * op).tr()`` and the state at each time ``t``. For
            callable functions, ``f``, the result is computed using
            ``f(t, ado_state)``. The values are stored in ``expect`` on
            (see the return section below).

        ado_init: bool, default False
            Indicates if initial condition is just the system state, or a
            numpy array including all ADOs.

        ado_return: bool, default True
            Whether to also return as output the full state of all ADOs.

        Returns
        -------
        :class:`qutip.solver.Result`
            The results of the simulation run, with the following attributes:

            * ``times``: the times ``t`` (i.e. the ``tlist``).

            * ``states``: the system state at each time ``t`` (only available
              if ``e_ops`` was ``None`` or if the solver option
              ``store_states`` was set to ``True``).

            * ``ado_states``: the full ADO state at each time (only available
              if ``ado_return`` was set to ``True``). Each element is an
              instance of :class:`HierarchyADOsState`.            .
              The state of a particular ADO may be extracted from
              ``result.ado_states[i]`` by calling :meth:`.extract`.

            * ``expect``: the value of each ``e_ops`` at time ``t`` (only
              available if ``e_ops`` were given). If ``e_ops`` was passed
              as a dictionary, then ``expect`` will be a dictionary with
              the same keys as ``e_ops`` and values giving the list of
              outcomes for the corresponding key.
        """
        ...

class HSolverDL(HEOMSolver):
    """
    A helper class for creating an :class:`HEOMSolver` that is backwards
    compatible with the ``HSolverDL`` provided in ``qutip.nonmarkov.heom``
    in QuTiP 4.6 and below.

    See :class:`HEOMSolver` and :class:`DrudeLorentzBath` for more
    descriptions of the underlying solver and bath construction.

    An exact copy of the QuTiP 4.6 HSolverDL is provided in
    ``qutip.nonmarkov.dlheom_solver`` for cases where the functionality of
    the older solver is required. The older solver will be completely
    removed in QuTiP 5.

    .. note::

        Unlike the version of ``HSolverDL`` in QuTiP 4.6, this solver
        supports supplying a time-dependent or Liouvillian ``H_sys``.

    .. note::

        For compatibility with ``HSolverDL`` in QuTiP 4.6 and below, the
        parameter ``N_exp`` specifying the number of exponents to keep in
        the expansion of the bath correlation function is one more than
        the equivalent ``Nk`` used in the :class:`DrudeLorentzBath`. I.e.,
        ``Nk = N_exp - 1``. The ``Nk`` parameter in the
        :class:`DrudeLorentzBath` does not count the zeroeth exponent in
        order to better match common usage in the literature.

    .. note::

        The ``stats`` and ``renorm`` arguments accepted in QuTiP 4.6 and below
        are no longer supported.

    Parameters
    ----------
    H_sys : Qobj or QobjEvo or list
        The system Hamiltonian or Liouvillian. See :class:`HEOMSolver` for
        a complete description.

    coup_op : Qobj
        Operator describing the coupling between system and bath.
        See parameter ``Q`` in :class:`BosonicBath` for a complete description.

    coup_strength : float
        Coupling strength. Referred to as ``lam`` in :class:`DrudeLorentzBath`.

    temperature : float
        Bath temperature. Referred to as ``T`` in :class:`DrudeLorentzBath`.

    N_cut : int
        The maximum depth of the hierarchy. See ``max_depth`` in
        :class:`HEOMSolver` for a full description.

    N_exp : int
        Number of exponential terms used to approximate the bath correlation
        functions. The equivalent ``Nk`` in :class:`DrudeLorentzBath` is one
        less than ``N_exp`` (see note above).

    cut_freq : float
        Bath spectral density cutoff frequency. Referred to as ``gamma`` in
        :class:`DrudeLorentzBath`.

    bnd_cut_approx : bool
        Use boundary cut off approximation. If true, the Matsubara
        terminator is added to the system Liouvillian (and H_sys is
        promoted to a Liouvillian if it was a Hamiltonian).

    progress_bar : None, True or :class:`BaseProgressBar`
        Optional instance of BaseProgressBar, or a subclass thereof, for
        showing the progress of the solver. If True, an instance of
        :class:`TextProgressBar` is used instead.

    options : :class:`qutip.solver.Options`
        Generic solver options.
        If set to None the default options will be used.

    progress_bar : None, True or :class:`BaseProgressBar`
        Optional instance of BaseProgressBar, or a subclass thereof, for
        showing the progress of the solver. If True, an instance of
        :class:`TextProgressBar` is used instead.

    combine : bool, default True
        Whether to combine exponents with the same frequency (and coupling
        operator). See :meth:`BosonicBath.combine` for details.
    """

    def __init__(self, H_sys, coup_op, coup_strength, temperature, N_cut, N_exp, cut_freq, bnd_cut_approx=False, options=None, progress_bar=None, combine=True):
        ...

class _GatherHEOMRHS:
    """ A class for collecting elements of the right-hand side matrix
        of the HEOM.

        Parameters
        ----------
        f_idx: function(he_state) -> he_idx
            A function that returns the index of a hierarchy state
            (i.e. an ADO label).
        block : int
            The size of a single ADO Liovillian operator in the hierarchy.
        nhe : int
            The number of ADOs in the hierarchy.
    """

    def __init__(self, f_idx, block, nhe):
        ...

    def add_op(self, row_he, col_he, op):
        """ Add an block operator to the list. """
        ...

    def gather(self):
        """ Create the HEOM liouvillian from a sorted list of smaller (fast) CSR
            matrices.

            .. note::

                The list of operators contains tuples of the form
                ``(row_idx, col_idx, op)``. The row_idx and col_idx give the
                *block* row and column for each op. An operator with
                block indices ``(N, M)`` is placed at position
                ``[N * block: (N + 1) * block, M * block: (M + 1) * block]``
                in the output matrix.

            Returns
            -------
            rhs : :obj:`qutip.fastsparse.fast_csr_matrix`
                A combined matrix of shape ``(block * nhe, block * ne)``.
        """
        ...
