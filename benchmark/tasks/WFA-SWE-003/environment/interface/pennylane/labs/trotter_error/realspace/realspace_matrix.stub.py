# 接口说明（仅签名与文档字符串，函数体已省略）。此文件在起点仓库中不存在，需要新建。
"""The RealspaceMatrix class"""

class RealspaceMatrix(Fragment):
    """Implements a dictionary of :class:`~.pennylane.labs.trotter_error.RealspaceSum` objects.

    This can be used to represent the fragments of a vibronic Hamiltonian given by, Eq. 3
    of `arXiv:2411.13669 <https://arxiv.org/abs/2411.13669v1>`_,

    .. math:: V_{i,j} = \\lambda_{i,j} + \\sum_{r} \\phi^{(1)}_{i,j,r} Q_r + \\sum_{r,s} \\phi^{(2)}_{i,j,r,s} Q_r Q_s + \\sum_{r,s,t} \\phi^{(3)}_{i,j,r,s,t} Q_r Q_s Q_t + \\dots,

    where the dictionary is indexed by tuples :math:`(i, j)` and the values are
    :class:`~.RealspaceSum` objects representing the operator :math:`V_{i,j}`.

    Args:
        states (int): the number of electronic states
        modes (int): the number of vibrational modes
        blocks (Dict[Tuple[int, int], RealspaceSum): a dictionary representation of the block matrix

    **Example**

    >>> from pennylane.labs.trotter_error import RealspaceOperator, RealspaceSum, RealspaceCoeffs, RealspaceMatrix
    >>> import numpy as np
    >>> n_states = 1
    >>> n_modes = 5
    >>> op1 = RealspaceOperator(n_modes, (), RealspaceCoeffs(np.array(1)))
    >>> op2 = RealspaceOperator(n_modes, ("Q"), RealspaceCoeffs(np.array([1, 2, 3, 4, 5]), label="phi"))
    >>> rs_sum = RealspaceSum(n_modes, [op1, op2])
    >>> RealspaceMatrix(n_states, n_modes, {(0, 0): rs_sum})
    RealspaceMatrix({(0, 0): RealspaceSum((RealspaceOperator(5, (), 1), RealspaceOperator(5, 'Q', phi[idx0])))})
    """

    def __init__(self, states: int, modes: int, blocks: Dict[Tuple[int, int], RealspaceSum]=None) -> RealspaceMatrix:
        ...

    def block(self, row: int, col: int) -> RealspaceSum:
        """Return the :class:`~.pennylane.labs.trotter_error.RealspaceSum` object located at the
        ``(row, col)`` entry of the :class:`~.pennylane.labs.trotter_error.RealspaceMatrix`.

        Args:
            row (int): the row of the index
            col (int): the column of the index

        Returns:
            RealspaceSum: the :class:`~.pennylane.labs.trotter_error.RealspaceSum` object indexed
                at ``(row, col)``

        **Example**

        >>> from pennylane.labs.trotter_error import RealspaceOperator, RealspaceSum, RealspaceCoeffs, RealspaceMatrix
        >>> import numpy as np
        >>> n_states = 1
        >>> n_modes = 5
        >>> op1 = RealspaceOperator(n_modes, (), RealspaceCoeffs(np.array(1)))
        >>> op2 = RealspaceOperator(n_modes, ("Q"), RealspaceCoeffs(np.array([1, 2, 3, 4, 5]), label="phi"))
        >>> rs_sum = RealspaceSum(n_modes, [op1, op2])
        >>> RealspaceMatrix(n_states, n_modes, {(0, 0): rs_sum}).block(0, 0)
        RealspaceSum((RealspaceOperator(5, (), 1), RealspaceOperator(5, 'Q', phi[idx0])))
        """
        ...

    def set_block(self, row: int, col: int, rs_sum: RealspaceSum) -> None:
        """Set the value of the block indexed at ``(row, col)``.

        Args:
            row (int): the row of the index
            col (int): the column of the index
            rs_sum (RealspaceSum): the :class:`~.pennylane.labs.trotter_error.RealspaceSum` object to stored in index ``(row, col)``

        Returns:
            None

        >>> from pennylane.labs.trotter_error import RealspaceOperator, RealspaceSum, RealspaceCoeffs, RealspaceMatrix
        >>> import numpy as np
        >>> n_states = 2
        >>> n_modes = 5
        >>> op1 = RealspaceOperator(n_modes, (), RealspaceCoeffs(np.array(1)))
        >>> op2 = RealspaceOperator(n_modes, ("Q"), RealspaceCoeffs(np.array([1, 2, 3, 4, 5]), label="phi"))
        >>> rs_sum = RealspaceSum(n_modes, [op1, op2])
        >>> vib = RealspaceMatrix(n_states, n_modes, {(0, 0): rs_sum})
        >>> vib
        RealspaceMatrix({(0, 0): RealspaceSum((RealspaceOperator(5, (), 1), RealspaceOperator(5, 'Q', phi[idx0])))})
        >>> vib.set_block(1, 1, rs_sum)
        >>> vib
        RealspaceMatrix({(0, 0): RealspaceSum((RealspaceOperator(5, (), 1), RealspaceOperator(5, 'Q', phi[idx0]))), (1, 1): RealspaceSum((RealspaceOperator(5, (), 1), RealspaceOperator(5, 'Q', phi[idx0])))})
        """
        ...

    def matrix(self, gridpoints: int, sparse: bool=False, basis: str='realspace') -> Union[np.ndarray, sp.sparse.csr_matrix]:
        """Return a matrix representation of the operator.

        Args:
            gridpoints (int): the number of gridpoints used to discretize the position or momentum operators
            basis (str): the basis of the matrix, available options are ``realspace`` and ``harmonic``
            sparse (bool): if ``True`` returns a sparse matrix, otherwise returns a dense matrix

        Returns:
            Union[ndarray, scipy.sparse.csr_array]: the matrix representation of the :class:`~.pennylane.labs.trotter_error.RealspaceOperator`

        **Example**

        >>> from pennylane.labs.trotter_error import RealspaceOperator, RealspaceSum, RealspaceCoeffs, RealspaceMatrix
        >>> import numpy as np
        >>> n_states = 1
        >>> n_modes = 5
        >>> op1 = RealspaceOperator(n_modes, (), RealspaceCoeffs(np.array(1)))
        >>> op2 = RealspaceOperator(n_modes, ("Q"), RealspaceCoeffs(np.array([1, 2, 3, 4, 5]), label="phi"))
        >>> rs_sum = RealspaceSum(n_modes, [op1, op2])
        >>> RealspaceMatrix(n_states, n_modes, {(0, 0): rs_sum}).matrix(2)
        [[-25.58680776   0.           0.         ...   0.           0.
            0.        ]
         [  0.         -16.72453851   0.         ...   0.           0.
            0.        ]
         [  0.           0.         -18.49699236 ...   0.           0.
            0.        ]
         ...
         [  0.           0.           0.         ...  -6.0898154    0.
            0.        ]
         [  0.           0.           0.         ...   0.          -7.86226925
            0.        ]
         [  0.           0.           0.         ...   0.           0.
            1.        ]]
        """
        ...

    def norm(self, params: Dict) -> float:
        """Returns an upper bound on the spectral norm of the operator.

        Args:
            params (dict[str, Union[int, bool]]): The dictionary of parameters. The supported parameters are

                * ``gridpoints`` (int): the number of gridpoints used to discretize the operator
                * ``sparse`` (bool): If ``True``, use optimizations for sparse operators. Defaults to ``False``.

        Returns:
            float: an upper bound on the spectral norm of the operator

        **Example**

        >>> from pennylane.labs.trotter_error import RealspaceOperator, RealspaceSum, RealspaceCoeffs, RealspaceMatrix
        >>> import numpy as np
        >>> n_states = 1
        >>> n_modes = 5
        >>> op1 = RealspaceOperator(n_modes, (), RealspaceCoeffs(np.array(1)))
        >>> op2 = RealspaceOperator(n_modes, ("Q"), RealspaceCoeffs(np.array([1, 2, 3, 4, 5]), label="phi"))
        >>> rs_sum = RealspaceSum(n_modes, [op1, op2])
        >>> params = {"gridpoints": 2, "sparse": True}
        >>> RealspaceMatrix(n_states, n_modes, {(0, 0): rs_sum}).norm(params)
        27.586807763582737
        """
        ...

    def __add__(self, other: RealspaceMatrix) -> RealspaceMatrix:
        ...

    def __sub__(self, other: RealspaceMatrix) -> RealspaceMatrix:
        ...

    def __mul__(self, scalar: float) -> RealspaceMatrix:
        ...
    __rmul__ = __mul__

    def __imul__(self, scalar: float) -> RealspaceMatrix:
        ...

    def __matmul__(self, other: RealspaceMatrix) -> RealspaceMatrix:
        ...

    def __eq__(self, other: RealspaceMatrix):
        ...

    def apply(self, state: VibronicHO) -> VibronicHO:
        """Apply the :class:`~.pennylane.labs.trotter_error.RealspaceMatrix` to an input :class:`~.pennylane.labs.trotter_error.VibronicHO` on the right.

        Args:
            state (VibronicHO): a vibronic wavefunction

        Returns:
            VibronicHO: the result of applying the :class:`~.pennylane.labs.trotter_error.RealspaceMatrix` to ``state``

        **Example**

        >>> from pennylane.labs.trotter_error import RealspaceOperator, RealspaceSum, RealspaceCoeffs, RealspaceMatrix
        >>> from pennylane.labs.trotter_error import HOState, VibronicHO
        >>> import numpy as np
        >>> n_states = 1
        >>> n_modes = 3
        >>> gridpoints = 2
        >>> op1 = RealspaceOperator(n_modes, (), RealspaceCoeffs.coeffs(np.array(1), label="lambda"))
        >>> op2 = RealspaceOperator(n_modes, ("Q"), RealspaceCoeffs.coeffs(np.array([1, 2, 3, 4, 5]), label="phi"))
        >>> rs_sum = RealspaceSum(n_modes, [op1, op2])
        >>> vib_matrix = RealspaceMatrix(n_states, n_modes, {(0, 0): rs_sum})
        >>> state_dict = {(1, 0, 0): 1, (0, 1, 1): 1}
        >>> state = HOState.from_dict(n_modes, gridpoints, state_dict)
        >>> VibronicHO(n_states, n_modes, gridpoints, [state])
        VibronicHO([HOState(modes=3, gridpoints=2, <Compressed Sparse Row sparse array of dtype 'int64'
            with 2 stored elements and shape (8, 1)>
          Coords	Values
          (3, 0)	1
          (4, 0)	1)])
        """
        ...

    def get_coefficients(self, threshold: float=0.0) -> Dict[Tuple[int, int], Dict]:
        """Return a dictionary containing the coefficients of the :class:`~.pennylane.labs.trotter_error.RealspaceSum`

        Args:
            threshold (float): tolerance to return coefficients whose magnitude is greater than ``threshold``

        Returns:
            Dict: a dictionary whose keys are the indices of the :class:`~.pennylane.labs.trotter_error.RealspaceMatrix` and whose values are dictionaries obtained by :func:`~pennylane.labs.trotter_error.RealspaceSum.get_coefficients`

        **Example**

        >>> from pennylane.labs.trotter_error import RealspaceOperator, RealspaceSum, RealspaceCoeffs, RealspaceMatrix
        >>> import numpy as np
        >>> n_states = 1
        >>> n_modes = 5
        >>> op1 = RealspaceOperator(n_modes, ("Q"), RealspaceCoeffs(np.array([1, 2, 3, 4, 5]), label="phi"))
        >>> op2 = RealspaceOperator(n_modes, ("P"), RealspaceCoeffs(np.array([1, 2, 3, 4, 5]), label="chi"))
        >>> rs_sum = RealspaceSum(n_modes, [op1, op2])
        >>> RealspaceMatrix(n_states, n_modes, {(0, 0): rs_sum}).get_coefficients()
        {(0, 0): {'Q': {(0,): 1.0, (1,): 2.0, (2,): 3.0, (3,): 4.0, (4,): 5.0},
        'P': {(0,): 1.0, (1,): 2.0, (2,): 3.0, (3,): 4.0, (4,): 5.0}}}
        """
        ...

    @classmethod
    def zero(cls, states: int, modes: int) -> RealspaceMatrix:
        """Return a RealspaceMatrix representation of the zero operator"""
        ...
