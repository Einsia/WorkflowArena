# Target interface (signatures + docstrings; function bodies omitted)

The following public interfaces must be provided. Names marked "internal interface used directly by the tests" are also imported/called directly by the hidden tests and must be provided with the same name and signature.

## `astropy.utils.masked.core`  (file `astropy/utils/masked/core.py`)

```python
__all__ = ['Masked', 'MaskedNDArray']

class Masked(NDArrayShapeMethods):
    r"""A scalar value or array of values with associated mask.

    The resulting instance will take its exact type from whatever the
    contents are, with the type generated on the fly as needed.

    Parameters
    ----------
    data : array-like
        The data for which a mask is to be added.  The result will be a
        a subclass of the type of ``data``.
    mask : array-like of bool, optional
        The initial mask to assign.  If not given, taken from the data.
    copy : bool
        Whether the data and mask should be copied. Default: `False`.
    """

    def __new__(cls, *args, **kwargs):
        ...

    @classmethod
    def from_unmasked(cls, data, mask=None, copy=False):
        r"""Create an instance from unmasked data and a mask.
        """
        ...

    @property
    def unmasked(self):
        r"""The unmasked values.

        See Also
        --------
        filled
        """
        ...

    def filled(self, fill_value):
        r"""Get a copy of the underlying data, with masked values filled in.

        Parameters
        ----------
        fill_value : object
            Value to replace masked values with.

        See Also
        --------
        unmasked
        """
        ...

    def __setitem__(self, item, value):
        ...

# [internal interface used directly by the tests]
class MaskedNDArrayInfo(ParentDtypeInfo):
    r"""Container for meta information like name, description, format.
    """

    def __init__(self, bound=False):
        ...

# [internal interface used directly by the tests]
class MaskedArraySubclassInfo:
    r"""Mixin class to create a subclasses such as MaskedQuantityInfo.
    """

# [internal interface used directly by the tests]
class MaskedIterator:
    r"""Flat iterator object to iterate over Masked Arrays.

    A `~astropy.utils.masked.MaskedIterator` iterator is returned by ``m.flat``
    for any masked array ``m``.  It allows iterating over the array as if it
    were a 1-D array, either in a for-loop or by calling its `next` method.

    Iteration is done in C-contiguous style, with the last index varying the
    fastest. The iterator can also be indexed using basic slicing or
    advanced indexing.

    Notes
    -----
    The design of `~astropy.utils.masked.MaskedIterator` follows that of
    `~numpy.ma.core.MaskedIterator`.  It is not exported by the
    `~astropy.utils.masked` module.  Instead of instantiating directly,
    use the ``flat`` method in the masked array instance.
    """

    def __init__(self, m):
        ...

    def __iter__(self):
        ...

    def __getitem__(self, indx):
        ...

    def __setitem__(self, index, value):
        ...

class MaskedNDArray(Masked, np.ndarray, base_cls=np.ndarray, data_cls=np.ndarray):

    def __new__(cls, *args, mask=None, **kwargs):
        r"""Get data class instance from arguments and then set mask.
        """
        ...

    @classmethod
    def from_unmasked(cls, data, mask=None, copy=False):
        ...

    @property
    def unmasked(self):
        ...

    @property
    def flat(self):
        r"""A 1-D iterator over the Masked array.

        This returns a ``MaskedIterator`` instance, which behaves the same
        as the `~numpy.flatiter` instance returned by `~numpy.ndarray.flat`,
        and is similar to Python's built-in iterator, except that it also
        allows assignment.
        """
        ...

    def view(self, dtype=None, type=None):
        r"""New view of the masked array.

        Like `numpy.ndarray.view`, but always returning a masked array subclass.
        """
        ...

    def __array_finalize__(self, obj):
        ...

    @property
    def shape(self):
        ...

    @shape.setter
    def shape(self, shape):
        ...

    def __eq__(self, other):
        ...

    def __array_ufunc__(self, ufunc, method, *inputs, **kwargs):
        ...

    def __array_function__(self, function, types, args, kwargs):
        ...

    def trace(self, offset=0, axis1=0, axis2=1, dtype=None, out=None):
        ...

    def min(self, axis=None, out=None, **kwargs):
        ...

    def max(self, axis=None, out=None, **kwargs):
        ...

    def nonzero(self):
        ...

    def compress(self, condition, axis=None, out=None):
        ...

    def repeat(self, repeats, axis=None):
        ...

    def choose(self, choices, out=None, mode='raise'):
        ...

    def argmin(self, axis=None, out=None):
        ...

    def argmax(self, axis=None, out=None):
        ...

    def argsort(self, axis=-1, kind=None, order=None):
        r"""Returns the indices that would sort an array.

        Perform an indirect sort along the given axis on both the array
        and the mask, with masked items being sorted to the end.

        Parameters
        ----------
        axis : int or None, optional
            Axis along which to sort.  The default is -1 (the last axis).
            If None, the flattened array is used.
        kind : str or None, ignored.
            The kind of sort.  Present only to allow subclasses to work.
        order : str or list of str.
            For an array with fields defined, the fields to compare first,
            second, etc.  A single field can be specified as a string, and not
            all fields need be specified, but unspecified fields will still be
            used, in dtype order, to break ties.

        Returns
        -------
        index_array : ndarray, int
            Array of indices that sorts along the specified ``axis``.  Use
            ``np.take_along_axis(self, index_array, axis=axis)`` to obtain
            the sorted array.
        """
        ...

    def sort(self, axis=-1, kind=None, order=None):
        r"""Sort an array in-place. Refer to `numpy.sort` for full documentation.
        """
        ...

    def argpartition(self, kth, axis=-1, kind='introselect', order=None):
        ...

    def partition(self, kth, axis=-1, kind='introselect', order=None):
        ...

    def cumsum(self, axis=None, dtype=None, out=None):
        ...

    def cumprod(self, axis=None, dtype=None, out=None):
        ...

    def clip(self, min=None, max=None, out=None, **kwargs):
        r"""Return an array whose values are limited to ``[min, max]``.

        Like `~numpy.clip`, but any masked values in ``min`` and ``max``
        are ignored for clipping.  The mask of the input array is propagated.
        """
        ...

    def mean(self, axis=None, dtype=None, out=None, keepdims=False):
        ...

    def var(self, axis=None, dtype=None, out=None, ddof=0, keepdims=False):
        ...

    def std(self, axis=None, dtype=None, out=None, ddof=0, keepdims=False):
        ...

    def any(self, axis=None, out=None, keepdims=False):
        ...

    def all(self, axis=None, out=None, keepdims=False):
        ...

    def __str__(self):
        ...

    def __repr__(self):
        ...

# [internal interface used directly by the tests]
class MaskedRecarray(np.recarray, MaskedNDArray, data_cls=np.recarray):

    def __array_finalize__(self, obj):
        ...

    def getfield(self, dtype, offset=0):
        ...

    def setfield(self, val, dtype, offset=0):
        ...

```

## `astropy.utils.masked.function_helpers`  (file `astropy/utils/masked/function_helpers.py`)

```python
# [name used directly by the tests]
MASKED_SAFE_FUNCTIONS = set()

# [name used directly by the tests]
APPLY_TO_BOTH_FUNCTIONS = {}

# [name used directly by the tests]
DISPATCHED_FUNCTIONS = {}

# [name used directly by the tests]
UNSUPPORTED_FUNCTIONS = set()

# [name used directly by the tests]
IGNORED_FUNCTIONS = {
    # Deprecated
    np.asscalar,
    # I/O - useless for Masked, since no way to store the mask.
    np.save, np.savez, np.savetxt, np.savez_compressed,
    # Polynomials
    np.poly, np.polyadd, np.polyder, np.polydiv, np.polyfit, np.polyint,
    np.polymul, np.polysub, np.polyval, np.roots, np.vander}

```
