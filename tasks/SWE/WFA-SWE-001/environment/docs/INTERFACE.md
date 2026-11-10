# Target interface (signatures + docstrings; function bodies omitted)

The following public interfaces must be provided. Names marked "internal interface used directly by the tests" are also imported/called directly by the hidden tests and must be provided with the same name and signature.

## `astropy.coordinates.spectral_coordinate`  (file `astropy/coordinates/spectral_coordinate.py`)

```python
__all__ = ['SpectralCoord']

# [internal interface used directly by the tests]
def _apply_relativistic_doppler_shift(scoord, velocity):
    r"""Given a `SpectralQuantity` and a velocity, return a new `SpectralQuantity`
    that is Doppler shifted by this amount.

    Note that the Doppler shift applied is the full relativistic one, so
    `SpectralQuantity` currently expressed in velocity and not using the
    relativistic convention will temporarily be converted to use the
    relativistic convention while the shift is applied.

    Positive velocities are assumed to redshift the spectral quantity,
    while negative velocities blueshift the spectral quantity.
    """
    ...

# [internal interface used directly by the tests]
def update_differentials_to_match(original, velocity_reference, preserve_observer_frame=False):
    r"""Given an original coordinate object, update the differentials so that
    the final coordinate is at the same location as the original coordinate
    but co-moving with the velocity reference object.

    If preserve_original_frame is set to True, the resulting object will be in
    the frame of the original coordinate, otherwise it will be in the frame of
    the velocity reference.
    """
    ...

# [internal interface used directly by the tests]
def attach_zero_velocities(coord):
    r"""Set the differentials to be stationary on a coordinate object.
    """
    ...

class SpectralCoord(SpectralQuantity):
    r"""A spectral coordinate with its corresponding unit.

    .. note:: The |SpectralCoord| class is new in Astropy v4.1 and should be
              considered experimental at this time. Note that we do not fully
              support cases where the observer and target are moving
              relativistically relative to each other, so care should be taken
              in those cases. It is possible that there will be API changes in
              future versions of Astropy based on user feedback. If you have
              specific ideas for how it might be improved, please  let us know
              on the `astropy-dev mailing list`_ or at
              http://feedback.astropy.org.

    Parameters
    ----------
    value : ndarray or `~astropy.units.Quantity` or `SpectralCoord`
        Spectral values, which should be either wavelength, frequency,
        energy, wavenumber, or velocity values.
    unit : str or `~astropy.units.Unit`
        Unit for the given spectral values.
    observer : `~astropy.coordinates.BaseCoordinateFrame` or `~astropy.coordinates.SkyCoord`, optional
        The coordinate (position and velocity) of observer. If no velocities
        are present on this object, the observer is assumed to be stationary
        relative to the frame origin.
    target : `~astropy.coordinates.BaseCoordinateFrame` or `~astropy.coordinates.SkyCoord`, optional
        The coordinate (position and velocity) of target. If no velocities
        are present on this object, the target is assumed to be stationary
        relative to the frame origin.
    radial_velocity : `~astropy.units.Quantity`, optional
        The radial velocity of the target with respect to the observer. This
        can only be specified if ``redshift`` is not specified.
    redshift : float, optional
        The relativistic redshift of the target with respect to the observer.
        This can only be specified if ``radial_velocity`` cannot be specified.
    doppler_rest : `~astropy.units.Quantity`, optional
        The rest value to use when expressing the spectral value as a velocity.
    doppler_convention : str, optional
        The Doppler convention to use when expressing the spectral value as a velocity.
    """

    @u.quantity_input(radial_velocity=u.km/u.s)
    def __new__(cls, value, unit=None,
                    observer=None, target=None,
                    radial_velocity=None, redshift=None,
                    **kwargs):
        ...

    def __array_finalize__(self, obj):
        ...

    def replicate(self, value=None, unit=None,
                      observer=None, target=None,
                      radial_velocity=None, redshift=None,
                      doppler_convention=None, doppler_rest=None,
                      copy=False):
        r"""Return a replica of the `SpectralCoord`, optionally changing the
        values or attributes.

        Note that no conversion is carried out by this method - this keeps
        all the values and attributes the same, except for the ones explicitly
        passed to this method which are changed.

        If ``copy`` is set to `True` then a full copy of the internal arrays
        will be made.  By default the replica will use a reference to the
        original arrays when possible to save memory.

        Parameters
        ----------
        value : ndarray or `~astropy.units.Quantity` or `SpectralCoord`, optional
            Spectral values, which should be either wavelength, frequency,
            energy, wavenumber, or velocity values.
        unit : str or `~astropy.units.Unit`
            Unit for the given spectral values.
        observer : `~astropy.coordinates.BaseCoordinateFrame` or `~astropy.coordinates.SkyCoord`, optional
            The coordinate (position and velocity) of observer.
        target : `~astropy.coordinates.BaseCoordinateFrame` or `~astropy.coordinates.SkyCoord`, optional
            The coordinate (position and velocity) of target.
        radial_velocity : `~astropy.units.Quantity`, optional
            The radial velocity of the target with respect to the observer.
        redshift : float, optional
            The relativistic redshift of the target with respect to the observer.
        doppler_rest : `~astropy.units.Quantity`, optional
            The rest value to use when expressing the spectral value as a velocity.
        doppler_convention : str, optional
            The Doppler convention to use when expressing the spectral value as a velocity.
        copy : bool, optional
            If `True`, and ``value`` is not specified, the values are copied to
            the new `SkyCoord` - otherwise a reference to the same values is used.

        Returns
        -------
        sc : `SpectralCoord` object
            Replica of this object
        """
        ...

    @property
    def quantity(self):
        r"""Convert the ``SpectralCoord`` to a `~astropy.units.Quantity`.
        Equivalent to ``self.view(u.Quantity)``.

        Returns
        -------
        `~astropy.units.Quantity`
            This object viewed as a `~astropy.units.Quantity`.
        """
        ...

    @property
    def observer(self):
        r"""The coordinates of the observer.

        Returns
        -------
        `~astropy.coordinates.BaseCoordinateFrame`
            The astropy coordinate frame representing the observation.
        """
        ...

    @observer.setter
    def observer(self, value):
        ...

    @property
    def target(self):
        r"""The coordinates of the target being observed.

        Returns
        -------
        `~astropy.coordinates.BaseCoordinateFrame`
            The astropy coordinate frame representing the target.
        """
        ...

    @target.setter
    def target(self, value):
        ...

    @property
    def radial_velocity(self):
        r"""Radial velocity of target relative to the observer.

        Returns
        -------
        `~astropy.units.Quantity`
            Radial velocity of target.

        Notes
        -----
        This is different from the ``.radial_velocity`` property of a
        coordinate frame in that this calculates the radial velocity with
        respect to the *observer*, not the origin of the frame.
        """
        ...

    @property
    def redshift(self):
        r"""Redshift of target relative to observer. Calculated from the radial
        velocity.

        Returns
        -------
        float
            Redshift of target.
        """
        ...

    @u.quantity_input(velocity=u.km/u.s)
    def with_observer_stationary_relative_to(self, frame, velocity=None, preserve_observer_frame=False):
        r"""A new  `SpectralCoord` with the velocity of the observer altered,
        but not the position.

        If a coordinate frame is specified, the observer velocities will be
        modified to be stationary in the specified frame. If a coordinate
        instance is specified, optionally with non-zero velocities, the
        observer velocities will be updated so that the observer is co-moving
        with the specified coordinates.

        Parameters
        ----------
        frame : str, `~astropy.coordinates.BaseCoordinateFrame` or `~astropy.coordinates.SkyCoord`
            The observation frame in which the observer will be stationary. This
            can be the name of a frame (e.g. 'icrs'), a frame class, frame instance
            with no data, or instance with data. This can optionally include
            velocities.
        velocity : `~astropy.units.Quantity`, optional
            If ``frame`` does not contain velocities, these can be specified as
            a 3-element `~astropy.units.Quantity`. In the case where this is
            also not specified, the velocities default to zero.
        preserve_observer_frame : bool
            If `True`, the final observer frame class will be the same as the
            original one, and if `False` it will be the frame of the velocity
            reference class.

        Returns
        -------
        new_coord : `SpectralCoord`
            The new coordinate object representing the spectral data
            transformed based on the observer's new velocity frame.
        """
        ...

    def with_radial_velocity_shift(self, target_shift=None, observer_shift=None):
        r"""Apply a velocity shift to this spectral coordinate.

        The shift can be provided as a redshift (float value) or radial
        velocity (`~astropy.units.Quantity` with physical type of 'speed').

        Parameters
        ----------
        target_shift : float or `~astropy.units.Quantity`
            Shift value to apply to current target.
        observer_shift : float or `~astropy.units.Quantity`
            Shift value to apply to current observer.

        Returns
        -------
        `SpectralCoord`
            New spectral coordinate with the target/observer velocity changed
            to incorporate the shift.
        """
        ...

    def to_rest(self):
        r"""Transforms the spectral axis to the rest frame.
        """
        ...

    def __repr__(self):
        ...

```

## `astropy.coordinates.spectral_quantity`  (file `astropy/coordinates/spectral_quantity.py`)

```python
__all__ = ['SpectralQuantity']

class SpectralQuantity(SpecificTypeQuantity):
    r"""One or more value(s) with spectral units.

    The spectral units should be those for frequencies, wavelengths, energies,
    wavenumbers, or velocities (interpreted as Doppler velocities relative to a
    rest spectral value). The advantage of using this class over the regular
    `~astropy.units.Quantity` class is that in `SpectralQuantity`, the
    ``u.spectral`` equivalency is enabled by default (allowing automatic
    conversion between spectral units), and a preferred Doppler rest value and
    convention can be stored for easy conversion to/from velocities.

    Parameters
    ----------
    value : ndarray or `~astropy.units.Quantity` or `SpectralQuantity`
        Spectral axis data values.
    unit : str or `~astropy.units.Unit`
        Unit for the given data.
    doppler_rest : `~astropy.units.Quantity`, optional
        The rest value to use for conversions from/to velocities
    doppler_convention : str, optional
        The convention to use when converting the spectral data to/from
        velocities.
    """

    def __new__(cls, value, unit=None,
                    doppler_rest=None, doppler_convention=None,
                    **kwargs):
        ...

    def __array_finalize__(self, obj):
        ...

    def __array_ufunc__(self, function, method, *inputs, **kwargs):
        ...

    @property
    def doppler_rest(self):
        r"""The rest value of the spectrum used for transformations to/from
        velocity space.

        Returns
        -------
        `~astropy.units.Quantity`
            Rest value as an astropy `~astropy.units.Quantity` object.
        """
        ...

    @doppler_rest.setter
    @quantity_input(value=SPECTRAL_UNITS)
    def doppler_rest(self, value):
        r"""New rest value needed for velocity-space conversions.

        Parameters
        ----------
        value : `~astropy.units.Quantity`
            Rest value.
        """
        ...

    @property
    def doppler_convention(self):
        r"""The defined convention for conversions to/from velocity space.

        Returns
        -------
        str
            One of 'optical', 'radio', or 'relativistic' representing the
            equivalency used in the unit conversions.
        """
        ...

    @doppler_convention.setter
    def doppler_convention(self, value):
        r"""New velocity convention used for velocity space conversions.

        Parameters
        ----------
        value

        Notes
        -----
        More information on the equations dictating the transformations can be
        found in the astropy documentation [1]_.

        References
        ----------
        .. [1] Astropy documentation: https://docs.astropy.org/en/stable/units/equivalencies.html#spectral-doppler-equivalencies
        """
        ...

    @quantity_input(doppler_rest=SPECTRAL_UNITS)
    def to(self, unit,
               equivalencies=[],
               doppler_rest=None,
               doppler_convention=None):
        r"""Return a new `~astropy.coordinates.SpectralQuantity` object with the specified unit.

        By default, the ``spectral`` equivalency will be enabled, as well as
        one of the Doppler equivalencies if converting to/from velocities.

        Parameters
        ----------
        unit : `~astropy.units.UnitBase` instance, str
            An object that represents the unit to convert to. Must be
            an `~astropy.units.UnitBase` object or a string parseable
            by the `~astropy.units` package, and should be a spectral unit.
        equivalencies : list of equivalence pairs, optional
            A list of equivalence pairs to try if the units are not
            directly convertible (along with spectral).  See :ref:`unit_equivalencies`.
            If not provided or ``[]``, spectral equivalencies will be used.
            If `None`, no equivalencies will be applied at all, not even any
            set globally or within a context.
        doppler_rest : `~astropy.units.Quantity`, optional
            The rest value used when converting to/from velocities. This will
            also be set at an attribute on the output
            `~astropy.coordinates.SpectralQuantity`.
        doppler_convention : {'relativistic', 'optical', 'radio'}, optional
            The Doppler convention used when converting to/from velocities.
            This will also be set at an attribute on the output
            `~astropy.coordinates.SpectralQuantity`.

        Returns
        -------
        `SpectralQuantity`
            New spectral coordinate object with data converted to the new unit.
        """
        ...

    def to_value(self, *args, **kwargs):
        ...

```

## `astropy.wcs.wcsapi.fitswcs`  (file `astropy/wcs/wcsapi/fitswcs.py`)

```python
# [name used directly by the tests]
VELOCITY_FRAMES = {
    'GEOCENT': 'gcrs',
    'BARYCENT': 'icrs',
    'HELIOCENT': 'hcrs',
    'LSRK': 'lsrk',
    'LSRD': 'lsrd'
}

```
