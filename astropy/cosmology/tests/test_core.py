# Licensed under a 3-clause BSD style license - see LICENSE.rst

"""Testing :mod:`astropy.cosmology.core`."""

##############################################################################
# IMPORTS

# STDLIB
import abc
import inspect
import pickle
from types import MappingProxyType

# THIRD PARTY
import pytest

import numpy as np

# LOCAL
import astropy.cosmology.units as cu
import astropy.units as u
from astropy.cosmology import Cosmology, core
from astropy.cosmology.core import _COSMOLOGY_CLASSES
from astropy.cosmology.parameter import Parameter
from astropy.table import QTable, Table, Column
from astropy.utils.exceptions import AstropyDeprecationWarning
from astropy.utils.metadata import MetaData

from .test_connect import ReadWriteTestMixin, ToFromFormatTestMixin
from .test_parameter import ParameterTestMixin

##############################################################################
# SETUP / TEARDOWN


scalar_zs = [
    0, 1, 1100,  # interesting times
    # FIXME! np.inf breaks some funcs. 0 * inf is an error
    np.float64(3300),  # different type
    2 * cu.redshift, 3 * u.one  # compatible units
]
_zarr = np.linspace(0, 1e5, num=20)
array_zs = [
    _zarr,  # numpy
    _zarr.tolist(),  # pure python
    Column(_zarr),  # table-like
    _zarr * cu.redshift  # Quantity
]
valid_zs = scalar_zs + array_zs

invalid_zs = [
    (None, TypeError),  # wrong type
    # Wrong units (the TypeError is for the cython, which can differ)
    (4 * u.MeV, (u.UnitConversionError, TypeError)),  # scalar
    ([0, 1] * u.m, (u.UnitConversionError, TypeError)),  # array
]


class SubCosmology(Cosmology):
    """Defined here to be serializable."""

    H0 = Parameter(unit="km/(s Mpc)")
    Tcmb0 = Parameter(unit=u.K)
    m_nu = Parameter(unit=u.eV)

    def __init__(self, H0, Tcmb0=0*u.K, m_nu=0*u.eV, name=None, meta=None):
        super().__init__(name=name, meta=meta)
        self.H0 = H0
        self.Tcmb0 = Tcmb0
        self.m_nu = m_nu

    @property
    def is_flat(self):
        return super().is_flat()


##############################################################################
# TESTS
##############################################################################


class MetaTestMixin:
    """Tests for a :class:`astropy.utils.metadata.MetaData` on a Cosmology."""

    def test_meta_on_class(self, cosmo_cls):
        assert isinstance(cosmo_cls.meta, MetaData)

    def test_meta_on_instance(self, cosmo):
        assert isinstance(cosmo.meta, dict)  # test type
        # value set at initialization
        assert cosmo.meta == self.cls_kwargs.get("meta", {})

    def test_meta_mutable(self, cosmo):
        """The metadata is NOT immutable on a cosmology"""
        key = tuple(cosmo.meta.keys())[0]  # select some key
        cosmo.meta[key] = cosmo.meta.pop(key)  # will error if immutable


class TestCosmology(ParameterTestMixin, MetaTestMixin,
                    ReadWriteTestMixin, ToFromFormatTestMixin,
                    metaclass=abc.ABCMeta):
    """Test :class:`astropy.cosmology.Cosmology`.

    Subclasses should define tests for:

    - ``test_clone_change_param()``
    - ``test_repr()``
    """

    def setup_class(self):
        """
        Setup for testing.
        Cosmology should not be instantiated, so tests are done on a subclass.
        """
        # make sure SubCosmology is known
        _COSMOLOGY_CLASSES["SubCosmology"] = SubCosmology

        self.cls = SubCosmology
        self._cls_args = dict(H0=70 * (u.km / u.s / u.Mpc), Tcmb0=2.7 * u.K, m_nu=0.6 * u.eV)
        self.cls_kwargs = dict(name=self.__class__.__name__, meta={"a": "b"})

    def teardown_class(self):
        _COSMOLOGY_CLASSES.pop("SubCosmology", None)

    @property
    def cls_args(self):
        return tuple(self._cls_args.values())

    @property
    def ba(self):
        """Return filled `inspect.BoundArguments` for cosmology.

        Note this is not a fixture because those are cached and too easily
        mutated in-place, which is a difficult thing to diagnose.
        """
        ba = self.cls._init_signature.bind(*self.cls_args, **self.cls_kwargs)
        ba.apply_defaults()
        return ba

    @pytest.fixture
    def cosmo_cls(self):
        """The Cosmology class as a :func:`pytest.fixture`."""
        return self.cls

    @pytest.fixture
    def cosmo(self, cosmo_cls):
        """The cosmology instance with which to test."""
        ba = self.ba
        return cosmo_cls(*ba.args, **ba.kwargs)

    # ===============================================================
    # Method & Attribute Tests

    # ---------------------------------------------------------------
    # class-level

    def test_init_subclass(self, cosmo_cls):
        """Test creating subclasses registers classes and manages Parameters."""
        class InitSubclassTest(cosmo_cls):
            pass

        # test parameters
        assert InitSubclassTest.__parameters__ == cosmo_cls.__parameters__

        # test and cleanup registry
        registrant = _COSMOLOGY_CLASSES.pop(InitSubclassTest.__qualname__)
        assert registrant is InitSubclassTest

    def test_init_signature(self, cosmo_cls, cosmo):
        """Test class-property ``_init_signature``."""
        # test presence
        assert hasattr(cosmo_cls, "_init_signature")
        assert hasattr(cosmo, "_init_signature")

        # test internal consistency, so following tests can use either cls or instance.
        assert cosmo_cls._init_signature == cosmo._init_signature

        # test matches __init__, but without 'self'
        sig = inspect.signature(cosmo.__init__)  # (instances don't have self)
        assert set(sig.parameters.keys()) == set(cosmo._init_signature.parameters.keys())
        assert all(np.all(sig.parameters[k].default == p.default) for k, p in
                   cosmo._init_signature.parameters.items())

    # ---------------------------------------------------------------
    # instance-level

    def test_init(self, cosmo_cls):
        """Test initialization."""
        # Cosmology only does name and meta, but this subclass adds H0 & Tcmb0.
        cosmo = cosmo_cls(*self.cls_args, name="test_init", meta={"m": 1})
        assert cosmo.name == "test_init"
        assert cosmo.meta["m"] == 1

        # if meta is None, it is changed to a dict
        cosmo = cosmo_cls(*self.cls_args, name="test_init", meta=None)
        assert cosmo.meta == {}

    def test_name(self, cosmo):
        """Test property ``name``."""
        assert cosmo.name is cosmo._name  # accesses private attribute
        assert cosmo.name is None or isinstance(cosmo.name, str)  # type
        assert cosmo.name == self.cls_kwargs["name"]  # test has expected value

        # immutable
        with pytest.raises(AttributeError, match="can't set"):
            cosmo.name = None

    def test_is_flat(self, cosmo_cls, cosmo):
        """Test property ``is_flat``. It's an ABC."""
        with pytest.raises(NotImplementedError, match="is_flat is not implemented"):
            cosmo.is_flat

    # ------------------------------------------------
    # clone

    def test_clone_identical(self, cosmo):
        """Test method ``.clone()`` if no (kw)args."""
        assert cosmo.clone() is cosmo

    def test_clone_name(self, cosmo):
        """Test method ``.clone()`` name argument."""
        # test changing name. clone treats 'name' differently (see next test)
        c = cosmo.clone(name="cloned cosmo")
        assert c.name == "cloned cosmo"  # changed
        # show name is the only thing changed
        c._name = cosmo.name  # first change name back
        assert c == cosmo
        assert c.meta == cosmo.meta

        # now change a different parameter and see how 'name' changes
        c = cosmo.clone(meta={})
        assert c.name == cosmo.name + " (modified)"

    def test_clone_meta(self, cosmo):
        """Test method ``.clone()`` meta argument: updates meta, doesn't clear."""
        # start with no change
        c = cosmo.clone(meta=None)
        assert c.meta == cosmo.meta

        # add something
        c = cosmo.clone(meta=dict(test_clone_meta=True))
        assert c.meta["test_clone_meta"] is True
        c.meta.pop("test_clone_meta")  # remove from meta
        assert c.meta == cosmo.meta  # now they match

    def test_clone_change_param(self, cosmo):
        """
        Test method ``.clone()`` changing a(many) Parameter(s).
        Nothing here b/c no Parameters.
        """
        pass

    def test_clone_fail_unexpected_arg(self, cosmo):
        """Test when ``.clone()`` gets an unexpected argument."""
        with pytest.raises(TypeError, match="unexpected keyword argument"):
            newclone = cosmo.clone(not_an_arg=4)

    def test_clone_fail_positional_arg(self, cosmo):
        with pytest.raises(TypeError, match="1 positional argument"):
            cosmo.clone(None)

    # ---------------------------------------------------------------
    # comparison methods

    def test_is_equivalent(self, cosmo):
        """Test :meth:`astropy.cosmology.Cosmology.is_equivalent`."""
        # to self
        assert cosmo.is_equivalent(cosmo)

        # same class, different instance
        newclone = cosmo.clone(name="test_is_equivalent")
        assert cosmo.is_equivalent(newclone)
        assert newclone.is_equivalent(cosmo)

        # different class
        assert not cosmo.is_equivalent(2)

    def test_equality(self, cosmo):
        """Test method ``.__eq__()."""
        # wrong class
        assert (cosmo != 2) and (2 != cosmo)
        # correct
        assert cosmo == cosmo
        # different name <= not equal, but equivalent
        newcosmo = cosmo.clone(name="test_equality")
        assert (cosmo != newcosmo) and (newcosmo != cosmo)
        assert cosmo.__equiv__(newcosmo) and newcosmo.__equiv__(cosmo)

    # ---------------------------------------------------------------

    def test_repr(self, cosmo_cls, cosmo):
        """Test method ``.__repr__()``.

        This is a very general test and it is probably good to have a
        hard-coded comparison.
        """
        r = repr(cosmo)

        # class in string rep
        assert cosmo_cls.__qualname__ in r
        assert r.index(cosmo_cls.__qualname__) == 0  # it's the first thing
        r = r[len(cosmo_cls.__qualname__) + 1:]  # remove

        # name in string rep
        if cosmo.name is not None:
            assert f"name=\"{cosmo.name}\"" in r
            assert r.index("name=") == 0
            r = r[6 + len(cosmo.name) + 3:]  # remove

        # parameters in string rep
        ps = {k: getattr(cosmo, k) for k in cosmo.__parameters__}
        cps = {k: getattr(cosmo_cls, k) for k in cosmo.__parameters__}
        for k, v in ps.items():
            sv = format(v, cps[k].format_spec if v is not None else '')
            assert (k + '=' + sv) in r
            assert r.index(k) == 0
            r = r[len((k + '=' + sv)) + 2:]  # remove

    # ------------------------------------------------

    @pytest.mark.parametrize("in_meta", [True, False])
    @pytest.mark.parametrize("table_cls", [Table, QTable])
    def test_astropy_table(self, cosmo, table_cls, in_meta):
        """Test ``astropy.table.Table(cosmology)``."""
        tbl = table_cls(cosmo, cosmology_in_meta=in_meta)

        assert isinstance(tbl, table_cls)
        # the name & all parameters are columns
        for n in ("name", *cosmo.__parameters__):
            assert n in tbl.colnames
            assert np.all(tbl[n] == getattr(cosmo, n))
        # check if Cosmology is in metadata or a column
        if in_meta:
            assert tbl.meta["cosmology"] == cosmo.__class__.__qualname__
            assert "cosmology" not in tbl.colnames
        else:
            assert "cosmology" not in tbl.meta
            assert tbl["cosmology"][0] == cosmo.__class__.__qualname__
        # the metadata is transferred
        for k, v in cosmo.meta.items():
            assert np.all(tbl.meta[k] == v)

    # ===============================================================
    # Usage Tests

    def test_immutability(self, cosmo):
        """
        Test immutability of cosmologies.
        The metadata is mutable: see ``test_meta_mutable``.
        """
        for n in cosmo.__all_parameters__:
            with pytest.raises(AttributeError):
                setattr(cosmo, n, getattr(cosmo, n))

    def test_pickle_class(self, cosmo_cls, pickle_protocol):
        """Test classes can pickle and unpickle."""
        # pickle and unpickle
        f = pickle.dumps(cosmo_cls, protocol=pickle_protocol)
        unpickled = pickle.loads(f)

        # test equality
        assert unpickled == cosmo_cls

    def test_pickle_instance(self, cosmo, pickle_protocol):
        """Test instances can pickle and unpickle."""
        # pickle and unpickle
        f = pickle.dumps(cosmo, protocol=pickle_protocol)
        with u.add_enabled_units(cu):
            unpickled = pickle.loads(f)

        assert unpickled == cosmo
        assert unpickled.meta == cosmo.meta


class CosmologySubclassTest(TestCosmology):
    """
    Test subclasses of :class:`astropy.cosmology.Cosmology`.
    This is broken away from ``TestCosmology``, because |Cosmology| is/will be
    an ABC and subclasses must override some methods.
    """

    @abc.abstractmethod
    def setup_class(self):
        """Setup for testing."""
        pass

    # ===============================================================
    # Method & Attribute Tests

    # ---------------------------------------------------------------
    # instance-level

    @abc.abstractmethod
    def test_is_flat(self, cosmo_cls, cosmo):
        """Test property ``is_flat``."""


# -----------------------------------------------------------------------------


class FlatCosmologyMixinTest:
    """Tests for :class:`astropy.cosmology.core.FlatCosmologyMixin` subclasses.

    E.g to use this class::

        class TestFlatSomeCosmology(FlatCosmologyMixinTest, TestSomeCosmology):
            ...
    """

    def test_is_flat(self, cosmo_cls, cosmo):
        """Test property ``is_flat``."""
        super().test_is_flat(cosmo_cls, cosmo)

        # it's always True
        assert cosmo.is_flat is True

    def test_is_equivalent(self, cosmo):
        """Test :meth:`astropy.cosmology.core.FlatCosmologyMixin.is_equivalent`.

        Normally this would pass up via super(), but ``__equiv__`` is meant
        to be overridden, so we skip super().
        e.g. FlatFLRWMixinTest -> FlatCosmologyMixinTest -> TestCosmology
        vs   FlatFLRWMixinTest -> FlatCosmologyMixinTest -> TestFLRW -> TestCosmology
        """
        CosmologySubclassTest.test_is_equivalent(self, cosmo)


# -----------------------------------------------------------------------------


def test_flrw_moved_deprecation():
    """Test the deprecation warning about the move of FLRW classes."""
    from astropy.cosmology import flrw

    # it's deprecated to import `flrw/*` from `core.py`
    with pytest.warns(AstropyDeprecationWarning):
        from astropy.cosmology.core import FLRW

    # but they are the same object
    assert FLRW is flrw.FLRW
