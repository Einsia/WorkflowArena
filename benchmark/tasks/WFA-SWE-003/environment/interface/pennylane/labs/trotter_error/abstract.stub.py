# 接口说明（仅签名与文档字符串，函数体已省略）。此文件在起点仓库中不存在，需要新建。
"""The Fragment class"""

class Fragment(ABC):
    """Abstract class used to define a fragment object for product formula error estimation.

    A :class:`~.Fragment` is an object that has a well-defined notion of a commutator. To ensure
    the existence of commutators, the implementation requires the following arithmetic dunder
    methods:

    * :meth:`~.__add__`: implements addition

    * :meth:`~.__mul__`: implements multiplication

    * :meth:`~.__matmul__`: implements matrix multiplication

    In addition to the arithmetic operators, a ``norm`` method should be defined. The norm is
    required to compute error estimates of Trotter error operators.
    """

    @abstractmethod
    def __add__(self, other: Fragment) -> Fragment:
        ...

    def __sub__(self, other: Fragment) -> Fragment:
        ...

    @abstractmethod
    def __mul__(self, scalar: float) -> Fragment:
        ...

    @abstractmethod
    def __matmul__(self, other: Fragment) -> Fragment:
        ...

    @abstractmethod
    def norm(self, params: Dict) -> float:
        """Compute the norm of the fragment.

        Args:
            params (Dict): A dictionary of parameters needed to compute the norm. It should be
                specified for each class inheriting from :class:`~.Fragment`.

        Returns:
            float: the norm of the :class:`~.Fragment`

        """
        ...

    @abstractmethod
    def apply(self, state: AbstractState) -> AbstractState:
        """Apply the Fragment to a state on the right. The type of ``state`` is determined by each class inheriting from ``Fragment``.

        Args:
            state (AbstractState): an object representing a quantum state

        Returns:
            AbstractState: the result of applying the ``Fragment`` to ``state``

        """
        ...

    def expectation(self, left: AbstractState, right: AbstractState) -> float:
        """Return the expectation value of a state. The type of ``state`` is determined by each class inheriting from ``Fragment``.

        Args:
            left (AbstractState): the state to be multiplied on the left of the ``Fragment``
            right (AbstractState): the state to be multiplied on the right of the ``Fragment``

        Returns:
            float: the expectation value obtained by applying ``Fragment`` to the given states
        """
        ...

def commutator(a: Fragment, b: Fragment) -> Fragment:
    """Return the commutator of two :class:`~.Fragment` objects

    Args:
        a (Fragment): the :class:`~.Fragment` on the left side of the commutator
        b (Fragment): the :class:`~.Fragment` on the right side of the commutator

    Returns:
        Fragment: the commutator ``[a, b]``
    """
    ...

def nested_commutator(fragments: Sequence[Fragment]) -> Fragment:
    """Return the nested commutator of a sequence of :class:`~.Fragment` objects

    Args:
        fragments (Sequence[Fragment]): a sequence of fragments

    Returns:
        Fragment: the nested commutator of the fragments
    """
    ...

class AbstractState(ABC):
    """Abstract class used to define a state object for product formula error estimation.

    A class inheriting from ``AbstractState`` must implement the following dunder methods.

    * ``__add__``: implements addition
    * ``__mul__``: implements multiplication

    Additionally, it requires the following methods.

    * ``zero_state``: returns a representation of the zero state
    * ``dot``: implments the dot product of two states
    """

    @abstractmethod
    def __add__(self, other: AbstractState) -> AbstractState:
        ...

    def __sub__(self, other: AbstractState) -> AbstractState:
        ...

    @abstractmethod
    def __mul__(self, scalar: float) -> AbstractState:
        ...

    @classmethod
    @abstractmethod
    def zero_state(cls) -> AbstractState:
        """Return a representation of the zero state.

        Returns:
            AbstractState: an ``AbstractState`` representation of the zero state
        """
        ...

    @abstractmethod
    def dot(self, other: AbstractState) -> float:
        """Compute the dot product of two states.

        Args:
            other (AbstractState): the state to take the dot product with

        Returns:
           float: the dot product of self and other
        """
        ...
