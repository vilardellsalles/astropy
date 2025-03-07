# Licensed under a 3-clause BSD style license - see LICENSE.rst

"""Stand-alone overall systems tests for :mod:`astropy.cosmology`."""

from io import StringIO

import pytest

import numpy as np

import astropy.constants as const
import astropy.units as u
from astropy.cosmology import Cosmology, flrw, funcs
from astropy.cosmology.realizations import Planck18
from astropy.units import allclose
from astropy.utils.compat.optional_deps import HAS_SCIPY
from astropy.utils.exceptions import AstropyUserWarning


@pytest.mark.skipif(not HAS_SCIPY, reason="requires scipy.")
def test_flat_z1():
    """Test a flat cosmology at z=1 against several other on-line calculators.

    Test values were taken from the following web cosmology calculators on
    2012-02-11:

    Wright: http://www.astro.ucla.edu/~wright/CosmoCalc.html
            (https://ui.adsabs.harvard.edu/abs/2006PASP..118.1711W)
    Kempner: http://www.kempner.net/cosmic.php
    iCosmos: http://www.icosmos.co.uk/index.html
    """
    cosmo = flrw.FlatLambdaCDM(H0=70, Om0=0.27, Tcmb0=0.0)

    # The order of values below is Wright, Kempner, iCosmos'
    assert allclose(cosmo.comoving_distance(1),
                    [3364.5, 3364.8, 3364.7988] * u.Mpc, rtol=1e-4)
    assert allclose(cosmo.angular_diameter_distance(1),
                    [1682.3, 1682.4, 1682.3994] * u.Mpc, rtol=1e-4)
    assert allclose(cosmo.luminosity_distance(1),
                    [6729.2, 6729.6, 6729.5976] * u.Mpc, rtol=1e-4)
    assert allclose(cosmo.lookback_time(1),
                    [7.841, 7.84178, 7.843] * u.Gyr, rtol=1e-3)
    assert allclose(cosmo.lookback_distance(1),
                    [2404.0, 2404.24, 2404.4] * u.Mpc, rtol=1e-3)


###############################################################################
# TODO! sort and refactor following tests.
# overall systems tests stay here, specific tests go to new test suite.

@pytest.mark.skipif('not HAS_SCIPY')
def test_units():
    """ Test if the right units are being returned"""

    cosmo = flrw.FlatLambdaCDM(H0=70, Om0=0.27, Tcmb0=2.0)
    assert cosmo.comoving_distance(1.0).unit == u.Mpc
    assert cosmo._comoving_distance_z1z2(1.0, 2.0).unit == u.Mpc
    assert cosmo.comoving_transverse_distance(1.0).unit == u.Mpc
    assert cosmo._comoving_transverse_distance_z1z2(1.0, 2.0).unit == u.Mpc
    assert cosmo.angular_diameter_distance(1.0).unit == u.Mpc
    assert cosmo.angular_diameter_distance_z1z2(1.0, 2.0).unit == u.Mpc
    assert cosmo.luminosity_distance(1.0).unit == u.Mpc
    assert cosmo.lookback_time(1.0).unit == u.Gyr
    assert cosmo.lookback_distance(1.0).unit == u.Mpc
    assert cosmo.H(1.0).unit == u.km / u.Mpc / u.s
    assert cosmo.Tcmb(1.0).unit == u.K
    assert cosmo.Tcmb([0.0, 1.0]).unit == u.K
    assert cosmo.Tnu(1.0).unit == u.K
    assert cosmo.Tnu([0.0, 1.0]).unit == u.K
    assert cosmo.arcsec_per_kpc_comoving(1.0).unit == u.arcsec / u.kpc
    assert cosmo.arcsec_per_kpc_proper(1.0).unit == u.arcsec / u.kpc
    assert cosmo.kpc_comoving_per_arcmin(1.0).unit == u.kpc / u.arcmin
    assert cosmo.kpc_proper_per_arcmin(1.0).unit == u.kpc / u.arcmin
    assert cosmo.critical_density(1.0).unit == u.g / u.cm ** 3
    assert cosmo.comoving_volume(1.0).unit == u.Mpc ** 3
    assert cosmo.age(1.0).unit == u.Gyr
    assert cosmo.distmod(1.0).unit == u.mag


@pytest.mark.skipif('not HAS_SCIPY')
def test_distance_broadcast():
    """ Test array shape broadcasting for functions with single
    redshift inputs"""

    cosmo = flrw.FlatLambdaCDM(H0=70, Om0=0.27,
                               m_nu=u.Quantity([0.0, 0.1, 0.011], u.eV))
    z = np.linspace(0.1, 1, 6)
    z_reshape2d = z.reshape(2, 3)
    z_reshape3d = z.reshape(3, 2, 1)
    # Things with units
    methods = ['comoving_distance', 'luminosity_distance',
               'comoving_transverse_distance', 'angular_diameter_distance',
               'distmod', 'lookback_time', 'age', 'comoving_volume',
               'differential_comoving_volume', 'kpc_comoving_per_arcmin']
    for method in methods:
        g = getattr(cosmo, method)
        value_flat = g(z)
        assert value_flat.shape == z.shape
        value_2d = g(z_reshape2d)
        assert value_2d.shape == z_reshape2d.shape
        value_3d = g(z_reshape3d)
        assert value_3d.shape == z_reshape3d.shape
        assert value_flat.unit == value_2d.unit
        assert value_flat.unit == value_3d.unit
        assert allclose(value_flat, value_2d.flatten())
        assert allclose(value_flat, value_3d.flatten())

    # Also test unitless ones
    methods = ['absorption_distance', 'Om', 'Ode', 'Ok', 'H',
               'w', 'de_density_scale', 'Onu', 'Ogamma',
               'nu_relative_density']
    for method in methods:
        g = getattr(cosmo, method)
        value_flat = g(z)
        assert value_flat.shape == z.shape
        value_2d = g(z_reshape2d)
        assert value_2d.shape == z_reshape2d.shape
        value_3d = g(z_reshape3d)
        assert value_3d.shape == z_reshape3d.shape
        assert allclose(value_flat, value_2d.flatten())
        assert allclose(value_flat, value_3d.flatten())

    # Test some dark energy models
    methods = ['Om', 'Ode', 'w', 'de_density_scale']
    for tcosmo in [flrw.LambdaCDM(H0=70, Om0=0.27, Ode0=0.5),
                   flrw.wCDM(H0=70, Om0=0.27, Ode0=0.5, w0=-1.2),
                   flrw.w0waCDM(H0=70, Om0=0.27, Ode0=0.5, w0=-1.2, wa=-0.2),
                   flrw.wpwaCDM(H0=70, Om0=0.27, Ode0=0.5,
                                wp=-1.2, wa=-0.2, zp=0.9),
                   flrw.w0wzCDM(H0=70, Om0=0.27, Ode0=0.5, w0=-1.2, wz=0.1)]:
        for method in methods:
            g = getattr(cosmo, method)
            value_flat = g(z)
            assert value_flat.shape == z.shape
            value_2d = g(z_reshape2d)
            assert value_2d.shape == z_reshape2d.shape
            value_3d = g(z_reshape3d)
            assert value_3d.shape == z_reshape3d.shape
            assert allclose(value_flat, value_2d.flatten())
            assert allclose(value_flat, value_3d.flatten())


def test_equality():
    """Test equality and equivalence."""
    # mismatched signatures, both directions.
    newcosmo = flrw.w0waCDM(**Planck18._init_arguments, Ode0=0.6)
    assert newcosmo != Planck18
    assert Planck18 != newcosmo


def test_xtfuncs():
    """ Test of absorption and lookback integrand"""
    cosmo = flrw.LambdaCDM(70, 0.3, 0.5, Tcmb0=2.725)
    z = np.array([2.0, 3.2])
    assert allclose(cosmo.lookback_time_integrand(3), 0.052218976654969378,
                    rtol=1e-4)
    assert allclose(cosmo.lookback_time_integrand(z),
                    [0.10333179, 0.04644541], rtol=1e-4)
    assert allclose(cosmo.abs_distance_integrand(3), 3.3420145059180402,
                    rtol=1e-4)
    assert allclose(cosmo.abs_distance_integrand(z),
                    [2.7899584, 3.44104758], rtol=1e-4)


# This class is to test whether the routines work correctly
# if one only overloads w(z)
class test_cos_sub(flrw.FLRW):
    def __init__(self):
        super().__init__(70.0, 0.27, 0.73, Tcmb0=0.0, name="test_cos")
        self._w0 = -0.9

    def w(self, z):
        return self._w0 * np.ones_like(z)


# Similar, but with neutrinos
class test_cos_subnu(flrw.FLRW):
    def __init__(self):
        super().__init__(70.0, 0.27, 0.73, Tcmb0=3.0, m_nu=0.1 * u.eV, name="test_cos_nu")
        self._w0 = -0.8

    def w(self, z):
        return self._w0 * np.ones_like(z)


@pytest.mark.skipif('not HAS_SCIPY')
def test_de_subclass():
    # This is the comparison object
    z = [0.2, 0.4, 0.6, 0.9]
    cosmo = flrw.wCDM(H0=70, Om0=0.27, Ode0=0.73, w0=-0.9, Tcmb0=0.0)
    # Values taken from Ned Wrights advanced cosmo calculator, Aug 17 2012
    assert allclose(cosmo.luminosity_distance(z),
                    [975.5, 2158.2, 3507.3, 5773.1] * u.Mpc, rtol=1e-3)
    # Now try the subclass that only gives w(z)
    cosmo = test_cos_sub()
    assert allclose(cosmo.luminosity_distance(z),
                    [975.5, 2158.2, 3507.3, 5773.1] * u.Mpc, rtol=1e-3)
    # Test efunc
    assert allclose(cosmo.efunc(1.0), 1.7489240754, rtol=1e-5)
    assert allclose(cosmo.efunc([0.5, 1.0]),
                    [1.31744953, 1.7489240754], rtol=1e-5)
    assert allclose(cosmo.inv_efunc([0.5, 1.0]),
                    [0.75904236, 0.57178011], rtol=1e-5)
    # Test de_density_scale
    assert allclose(cosmo.de_density_scale(1.0), 1.23114444, rtol=1e-4)
    assert allclose(cosmo.de_density_scale([0.5, 1.0]),
                    [1.12934694, 1.23114444], rtol=1e-4)

    # Add neutrinos for efunc, inv_efunc


@pytest.mark.skipif('not HAS_SCIPY')
def test_varyde_lumdist_mathematica():
    """Tests a few varying dark energy EOS models against a mathematica
    computation"""

    # w0wa models
    z = np.array([0.2, 0.4, 0.9, 1.2])
    cosmo = flrw.w0waCDM(H0=70, Om0=0.2, Ode0=0.8, w0=-1.1, wa=0.2, Tcmb0=0.0)
    assert allclose(cosmo.w0, -1.1)
    assert allclose(cosmo.wa, 0.2)

    assert allclose(cosmo.luminosity_distance(z),
                    [1004.0, 2268.62, 6265.76, 9061.84] * u.Mpc, rtol=1e-4)
    assert allclose(cosmo.de_density_scale(0.0), 1.0, rtol=1e-5)
    assert allclose(cosmo.de_density_scale([0.0, 0.5, 1.5]),
                    [1.0, 0.9246310669529021, 0.9184087000251957])

    cosmo = flrw.w0waCDM(H0=70, Om0=0.3, Ode0=0.7, w0=-0.9, wa=0.0, Tcmb0=0.0)
    assert allclose(cosmo.luminosity_distance(z),
                    [971.667, 2141.67, 5685.96, 8107.41] * u.Mpc, rtol=1e-4)
    cosmo = flrw.w0waCDM(H0=70, Om0=0.3, Ode0=0.7, w0=-0.9, wa=-0.5,
                         Tcmb0=0.0)
    assert allclose(cosmo.luminosity_distance(z),
                    [974.087, 2157.08, 5783.92, 8274.08] * u.Mpc, rtol=1e-4)

    # wpwa models
    cosmo = flrw.wpwaCDM(H0=70, Om0=0.2, Ode0=0.8, wp=-1.1, wa=0.2, zp=0.5,
                         Tcmb0=0.0)
    assert allclose(cosmo.wp, -1.1)
    assert allclose(cosmo.wa, 0.2)
    assert allclose(cosmo.zp, 0.5)
    assert allclose(cosmo.luminosity_distance(z),
                    [1010.81, 2294.45, 6369.45, 9218.95] * u.Mpc, rtol=1e-4)

    cosmo = flrw.wpwaCDM(H0=70, Om0=0.2, Ode0=0.8, wp=-1.1, wa=0.2, zp=0.9,
                         Tcmb0=0.0)
    assert allclose(cosmo.wp, -1.1)
    assert allclose(cosmo.wa, 0.2)
    assert allclose(cosmo.zp, 0.9)
    assert allclose(cosmo.luminosity_distance(z),
                    [1013.68, 2305.3, 6412.37, 9283.33] * u.Mpc, rtol=1e-4)


@pytest.mark.skipif('not HAS_SCIPY')
def test_matter():
    # Test non-relativistic matter evolution
    tcos = flrw.FlatLambdaCDM(70.0, 0.3, Ob0=0.045)
    assert allclose(tcos.Om0, 0.3)
    assert allclose(tcos.H0, 70.0 * u.km / u.s / u.Mpc)
    assert allclose(tcos.Om(0), 0.3)
    assert allclose(tcos.Ob(0), 0.045)
    z = np.array([0.0, 0.5, 1.0, 2.0])
    assert allclose(tcos.Om(z), [0.3, 0.59124088, 0.77419355, 0.92045455],
                    rtol=1e-4)
    assert allclose(tcos.Ob(z),
                    [0.045, 0.08868613, 0.11612903, 0.13806818], rtol=1e-4)
    assert allclose(tcos.Odm(z), [0.255, 0.50255474, 0.65806452, 0.78238636],
                    rtol=1e-4)
    # Consistency of dark and baryonic matter evolution with all
    # non-relativistic matter
    assert allclose(tcos.Ob(z) + tcos.Odm(z), tcos.Om(z))


@pytest.mark.skipif('not HAS_SCIPY')
def test_ocurv():
    # Test Ok evolution
    # Flat, boring case
    tcos = flrw.FlatLambdaCDM(70.0, 0.3)
    assert allclose(tcos.Ok0, 0.0)
    assert allclose(tcos.Ok(0), 0.0)
    z = np.array([0.0, 0.5, 1.0, 2.0])
    assert allclose(tcos.Ok(z), [0.0, 0.0, 0.0, 0.0],
                    rtol=1e-6)

    # Not flat
    tcos = flrw.LambdaCDM(70.0, 0.3, 0.5, Tcmb0=u.Quantity(0.0, u.K))
    assert allclose(tcos.Ok0, 0.2)
    assert allclose(tcos.Ok(0), 0.2)
    assert allclose(tcos.Ok(z), [0.2, 0.22929936, 0.21621622, 0.17307692],
                    rtol=1e-4)

    # Test the sum; note that Ogamma/Onu are 0
    assert allclose(tcos.Ok(z) + tcos.Om(z) + tcos.Ode(z),
                    [1.0, 1.0, 1.0, 1.0], rtol=1e-5)


@pytest.mark.skipif('not HAS_SCIPY')
def test_ode():
    # Test Ode evolution, turn off neutrinos, cmb
    tcos = flrw.FlatLambdaCDM(70.0, 0.3, Tcmb0=0)
    assert allclose(tcos.Ode0, 0.7)
    assert allclose(tcos.Ode(0), 0.7)
    z = np.array([0.0, 0.5, 1.0, 2.0])
    assert allclose(tcos.Ode(z), [0.7, 0.408759, 0.2258065, 0.07954545],
                    rtol=1e-5)


@pytest.mark.skipif('not HAS_SCIPY')
def test_ogamma():
    """Tests the effects of changing the temperature of the CMB"""

    # Tested against Ned Wright's advanced cosmology calculator,
    # Sep 7 2012.  The accuracy of our comparison is limited by
    # how many digits it outputs, which limits our test to about
    # 0.2% accuracy.  The NWACC does not allow one
    # to change the number of nuetrino species, fixing that at 3.
    # Also, inspection of the NWACC code shows it uses inaccurate
    # constants at the 0.2% level (specifically, a_B),
    # so we shouldn't expect to match it that well. The integral is
    # also done rather crudely.  Therefore, we should not expect
    # the NWACC to be accurate to better than about 0.5%, which is
    # unfortunate, but reflects a problem with it rather than this code.
    # More accurate tests below using Mathematica
    z = np.array([1.0, 10.0, 500.0, 1000.0])
    cosmo = flrw.FlatLambdaCDM(H0=70, Om0=0.3, Tcmb0=0, Neff=3)
    assert allclose(cosmo.angular_diameter_distance(z),
                    [1651.9, 858.2, 26.855, 13.642] * u.Mpc, rtol=5e-4)
    cosmo = flrw.FlatLambdaCDM(H0=70, Om0=0.3, Tcmb0=2.725, Neff=3)
    assert allclose(cosmo.angular_diameter_distance(z),
                    [1651.8, 857.9, 26.767, 13.582] * u.Mpc, rtol=5e-4)
    cosmo = flrw.FlatLambdaCDM(H0=70, Om0=0.3, Tcmb0=4.0, Neff=3)
    assert allclose(cosmo.angular_diameter_distance(z),
                    [1651.4, 856.6, 26.489, 13.405] * u.Mpc, rtol=5e-4)

    # Next compare with doing the integral numerically in Mathematica,
    # which allows more precision in the test.  It is at least as
    # good as 0.01%, possibly better
    cosmo = flrw.FlatLambdaCDM(H0=70, Om0=0.3, Tcmb0=0, Neff=3.04)
    assert allclose(cosmo.angular_diameter_distance(z),
                    [1651.91, 858.205, 26.8586, 13.6469] * u.Mpc, rtol=1e-5)
    cosmo = flrw.FlatLambdaCDM(H0=70, Om0=0.3, Tcmb0=2.725, Neff=3.04)
    assert allclose(cosmo.angular_diameter_distance(z),
                    [1651.76, 857.817, 26.7688, 13.5841] * u.Mpc, rtol=1e-5)
    cosmo = flrw.FlatLambdaCDM(H0=70, Om0=0.3, Tcmb0=4.0, Neff=3.04)
    assert allclose(cosmo.angular_diameter_distance(z),
                    [1651.21, 856.411, 26.4845, 13.4028] * u.Mpc, rtol=1e-5)

    # Just to be really sure, we also do a version where the integral
    # is analytic, which is a Ode = 0 flat universe.  In this case
    # Integrate(1/E(x),{x,0,z}) = 2 ( sqrt((1+Or z)/(1+z)) - 1 )/(Or - 1)
    # Recall that c/H0 * Integrate(1/E) is FLRW.comoving_distance.
    Ogamma0h2 = 4 * 5.670373e-8 / 299792458.0 ** 3 * 2.725 ** 4 / 1.87837e-26
    Onu0h2 = Ogamma0h2 * 7.0 / 8.0 * (4.0 / 11.0) ** (4.0 / 3.0) * 3.04
    Or0 = (Ogamma0h2 + Onu0h2) / 0.7 ** 2
    Om0 = 1.0 - Or0
    hubdis = (299792.458 / 70.0) * u.Mpc
    cosmo = flrw.FlatLambdaCDM(H0=70, Om0=Om0, Tcmb0=2.725, Neff=3.04)
    targvals = 2.0 * hubdis * \
        (np.sqrt((1.0 + Or0 * z) / (1.0 + z)) - 1.0) / (Or0 - 1.0)
    assert allclose(cosmo.comoving_distance(z), targvals, rtol=1e-5)

    # And integers for z
    assert allclose(cosmo.comoving_distance(z.astype(int)),
                    targvals, rtol=1e-5)

    # Try Tcmb0 = 4
    Or0 *= (4.0 / 2.725) ** 4
    Om0 = 1.0 - Or0
    cosmo = flrw.FlatLambdaCDM(H0=70, Om0=Om0, Tcmb0=4.0, Neff=3.04)
    targvals = 2.0 * hubdis * \
        (np.sqrt((1.0 + Or0 * z) / (1.0 + z)) - 1.0) / (Or0 - 1.0)
    assert allclose(cosmo.comoving_distance(z), targvals, rtol=1e-5)


@pytest.mark.skipif('not HAS_SCIPY')
def test_tcmb():
    cosmo = flrw.FlatLambdaCDM(70.4, 0.272, Tcmb0=2.5)
    assert allclose(cosmo.Tcmb0, 2.5 * u.K)
    assert allclose(cosmo.Tcmb(2), 7.5 * u.K)
    z = [0.0, 1.0, 2.0, 3.0, 9.0]
    assert allclose(cosmo.Tcmb(z),
                    [2.5, 5.0, 7.5, 10.0, 25.0] * u.K, rtol=1e-6)
    # Make sure it's the same for integers
    z = [0, 1, 2, 3, 9]
    assert allclose(cosmo.Tcmb(z),
                    [2.5, 5.0, 7.5, 10.0, 25.0] * u.K, rtol=1e-6)


@pytest.mark.skipif('not HAS_SCIPY')
def test_tnu():
    cosmo = flrw.FlatLambdaCDM(70.4, 0.272, Tcmb0=3.0)
    assert allclose(cosmo.Tnu0, 2.1412975665108247 * u.K, rtol=1e-6)
    assert allclose(cosmo.Tnu(2), 6.423892699532474 * u.K, rtol=1e-6)
    z = [0.0, 1.0, 2.0, 3.0]
    expected = [2.14129757, 4.28259513, 6.4238927, 8.56519027] * u.K
    assert allclose(cosmo.Tnu(z), expected, rtol=1e-6)

    # Test for integers
    z = [0, 1, 2, 3]
    assert allclose(cosmo.Tnu(z), expected, rtol=1e-6)


@pytest.mark.skipif('not HAS_SCIPY')
def test_efunc_vs_invefunc_flrw():
    """ Test that efunc and inv_efunc give inverse values"""
    z0 = 0.5
    z = np.array([0.5, 1.0, 2.0, 5.0])

    # FLRW is abstract, so requires test_cos_sub defined earlier
    # This requires scipy, unlike the built-ins, because it
    # calls de_density_scale, which has an integral in it
    cosmo = test_cos_sub()
    assert allclose(cosmo.efunc(z0), 1.0 / cosmo.inv_efunc(z0))
    assert allclose(cosmo.efunc(z), 1.0 / cosmo.inv_efunc(z))
    # Add neutrinos
    cosmo = test_cos_subnu()
    assert allclose(cosmo.efunc(z0), 1.0 / cosmo.inv_efunc(z0))
    assert allclose(cosmo.efunc(z), 1.0 / cosmo.inv_efunc(z))


@pytest.mark.skipif('not HAS_SCIPY')
def test_kpc_methods():
    cosmo = flrw.FlatLambdaCDM(70.4, 0.272, Tcmb0=0.0)
    assert allclose(cosmo.arcsec_per_kpc_comoving(3),
                             0.0317179167 * u.arcsec / u.kpc)
    assert allclose(cosmo.arcsec_per_kpc_proper(3),
                             0.1268716668 * u.arcsec / u.kpc)
    assert allclose(cosmo.kpc_comoving_per_arcmin(3),
                             1891.6753126 * u.kpc / u.arcmin)
    assert allclose(cosmo.kpc_proper_per_arcmin(3),
                             472.918828 * u.kpc / u.arcmin)


@pytest.mark.skipif('not HAS_SCIPY')
def test_comoving_volume():

    c_flat = flrw.LambdaCDM(H0=70, Om0=0.27, Ode0=0.73, Tcmb0=0.0)
    c_open = flrw.LambdaCDM(H0=70, Om0=0.27, Ode0=0.0, Tcmb0=0.0)
    c_closed = flrw.LambdaCDM(H0=70, Om0=2, Ode0=0.0, Tcmb0=0.0)

    # test against ned wright's calculator (cubic Gpc)
    redshifts = np.array([0.5, 1, 2, 3, 5, 9])
    wright_flat = np.array([29.123, 159.529, 630.427, 1178.531, 2181.485,
                            3654.802]) * u.Gpc**3
    wright_open = np.array([20.501, 99.019, 380.278, 747.049, 1558.363,
                            3123.814]) * u.Gpc**3
    wright_closed = np.array([12.619, 44.708, 114.904, 173.709, 258.82,
                              358.992]) * u.Gpc**3
    # The wright calculator isn't very accurate, so we use a rather
    # modest precision
    assert allclose(c_flat.comoving_volume(redshifts), wright_flat,
                             rtol=1e-2)
    assert allclose(c_open.comoving_volume(redshifts),
                             wright_open, rtol=1e-2)
    assert allclose(c_closed.comoving_volume(redshifts),
                             wright_closed, rtol=1e-2)


@pytest.mark.skipif('not HAS_SCIPY')
def test_differential_comoving_volume():
    from scipy.integrate import quad

    c_flat = flrw.LambdaCDM(H0=70, Om0=0.27, Ode0=0.73, Tcmb0=0.0)
    c_open = flrw.LambdaCDM(H0=70, Om0=0.27, Ode0=0.0, Tcmb0=0.0)
    c_closed = flrw.LambdaCDM(H0=70, Om0=2, Ode0=0.0, Tcmb0=0.0)

    # test that integration of differential_comoving_volume()
    #  yields same as comoving_volume()
    redshifts = np.array([0.5, 1, 2, 3, 5, 9])
    wright_flat = np.array([29.123, 159.529, 630.427, 1178.531, 2181.485,
                            3654.802]) * u.Gpc**3
    wright_open = np.array([20.501, 99.019, 380.278, 747.049, 1558.363,
                            3123.814]) * u.Gpc**3
    wright_closed = np.array([12.619, 44.708, 114.904, 173.709, 258.82,
                              358.992]) * u.Gpc**3
    # The wright calculator isn't very accurate, so we use a rather
    # modest precision.
    ftemp = lambda x: c_flat.differential_comoving_volume(x).value
    otemp = lambda x: c_open.differential_comoving_volume(x).value
    ctemp = lambda x: c_closed.differential_comoving_volume(x).value
    # Multiply by solid_angle (4 * pi)
    assert allclose(np.array([4.0 * np.pi * quad(ftemp, 0, redshift)[0]
                              for redshift in redshifts]) * u.Mpc**3,
                    wright_flat, rtol=1e-2)
    assert allclose(np.array([4.0 * np.pi * quad(otemp, 0, redshift)[0]
                              for redshift in redshifts]) * u.Mpc**3,
                    wright_open, rtol=1e-2)
    assert allclose(np.array([4.0 * np.pi * quad(ctemp, 0, redshift)[0]
                              for redshift in redshifts]) * u.Mpc**3,
                    wright_closed, rtol=1e-2)


@pytest.mark.skipif('not HAS_SCIPY')
def test_flat_open_closed_icosmo():
    """ Test against the tabulated values generated from icosmo.org
    with three example cosmologies (flat, open and closed).
    """

    cosmo_flat = """\
# from icosmo (icosmo.org)
# Om 0.3 w -1 h 0.7 Ol 0.7
# z     comoving_transvers_dist   angular_diameter_dist  luminosity_dist
       0.0000000       0.0000000       0.0000000         0.0000000
      0.16250000       669.77536       576.15085         778.61386
      0.32500000       1285.5964       970.26143         1703.4152
      0.50000000       1888.6254       1259.0836         2832.9381
      0.66250000       2395.5489       1440.9317         3982.6000
      0.82500000       2855.5732       1564.6976         5211.4210
       1.0000000       3303.8288       1651.9144         6607.6577
       1.1625000       3681.1867       1702.2829         7960.5663
       1.3250000       4025.5229       1731.4077         9359.3408
       1.5000000       4363.8558       1745.5423         10909.640
       1.6625000       4651.4830       1747.0359         12384.573
       1.8250000       4916.5970       1740.3883         13889.387
       2.0000000       5179.8621       1726.6207         15539.586
       2.1625000       5406.0204       1709.4136         17096.540
       2.3250000       5616.5075       1689.1752         18674.888
       2.5000000       5827.5418       1665.0120         20396.396
       2.6625000       6010.4886       1641.0890         22013.414
       2.8250000       6182.1688       1616.2533         23646.796
       3.0000000       6355.6855       1588.9214         25422.742
       3.1625000       6507.2491       1563.3031         27086.425
       3.3250000       6650.4520       1537.6768         28763.205
       3.5000000       6796.1499       1510.2555         30582.674
       3.6625000       6924.2096       1485.0852         32284.127
       3.8250000       7045.8876       1460.2876         33996.408
       4.0000000       7170.3664       1434.0733         35851.832
       4.1625000       7280.3423       1410.2358         37584.767
       4.3250000       7385.3277       1386.9160         39326.870
       4.5000000       7493.2222       1362.4040         41212.722
       4.6625000       7588.9589       1340.2135         42972.480
"""

    cosmo_open = """\
# from icosmo (icosmo.org)
# Om 0.3 w -1 h 0.7 Ol 0.1
# z     comoving_transvers_dist   angular_diameter_dist  luminosity_dist
       0.0000000       0.0000000       0.0000000       0.0000000
      0.16250000       643.08185       553.18868       747.58265
      0.32500000       1200.9858       906.40441       1591.3062
      0.50000000       1731.6262       1154.4175       2597.4393
      0.66250000       2174.3252       1307.8648       3614.8157
      0.82500000       2578.7616       1413.0201       4706.2399
       1.0000000       2979.3460       1489.6730       5958.6920
       1.1625000       3324.2002       1537.2024       7188.5829
       1.3250000       3646.8432       1568.5347       8478.9104
       1.5000000       3972.8407       1589.1363       9932.1017
       1.6625000       4258.1131       1599.2913       11337.226
       1.8250000       4528.5346       1603.0211       12793.110
       2.0000000       4804.9314       1601.6438       14414.794
       2.1625000       5049.2007       1596.5852       15968.097
       2.3250000       5282.6693       1588.7727       17564.875
       2.5000000       5523.0914       1578.0261       19330.820
       2.6625000       5736.9813       1566.4113       21011.694
       2.8250000       5942.5803       1553.6158       22730.370
       3.0000000       6155.4289       1538.8572       24621.716
       3.1625000       6345.6997       1524.4924       26413.975
       3.3250000       6529.3655       1509.6799       28239.506
       3.5000000       6720.2676       1493.3928       30241.204
       3.6625000       6891.5474       1478.0799       32131.840
       3.8250000       7057.4213       1462.6780       34052.058
       4.0000000       7230.3723       1446.0745       36151.862
       4.1625000       7385.9998       1430.7021       38130.224
       4.3250000       7537.1112       1415.4199       40135.117
       4.5000000       7695.0718       1399.1040       42322.895
       4.6625000       7837.5510       1384.1150       44380.133
"""

    cosmo_closed = """\
# from icosmo (icosmo.org)
# Om 2 w -1 h 0.7 Ol 0.1
# z     comoving_transvers_dist   angular_diameter_dist  luminosity_dist
       0.0000000       0.0000000       0.0000000       0.0000000
      0.16250000       601.80160       517.67879       699.59436
      0.32500000       1057.9502       798.45297       1401.7840
      0.50000000       1438.2161       958.81076       2157.3242
      0.66250000       1718.6778       1033.7912       2857.3019
      0.82500000       1948.2400       1067.5288       3555.5381
       1.0000000       2152.7954       1076.3977       4305.5908
       1.1625000       2312.3427       1069.2914       5000.4410
       1.3250000       2448.9755       1053.3228       5693.8681
       1.5000000       2575.6795       1030.2718       6439.1988
       1.6625000       2677.9671       1005.8092       7130.0873
       1.8250000       2768.1157       979.86398       7819.9270
       2.0000000       2853.9222       951.30739       8561.7665
       2.1625000       2924.8116       924.84161       9249.7167
       2.3250000       2988.5333       898.80701       9936.8732
       2.5000000       3050.3065       871.51614       10676.073
       2.6625000       3102.1909       847.01459       11361.774
       2.8250000       3149.5043       823.39982       12046.854
       3.0000000       3195.9966       798.99915       12783.986
       3.1625000       3235.5334       777.30533       13467.908
       3.3250000       3271.9832       756.52790       14151.327
       3.5000000       3308.1758       735.15017       14886.791
       3.6625000       3339.2521       716.19347       15569.263
       3.8250000       3368.1489       698.06195       16251.319
       4.0000000       3397.0803       679.41605       16985.401
       4.1625000       3422.1142       662.87926       17666.664
       4.3250000       3445.5542       647.05243       18347.576
       4.5000000       3469.1805       630.76008       19080.493
       4.6625000       3489.7534       616.29199       19760.729
"""

    redshifts, dm, da, dl = np.loadtxt(StringIO(cosmo_flat), unpack=1)
    dm = dm * u.Mpc
    da = da * u.Mpc
    dl = dl * u.Mpc
    cosmo = flrw.LambdaCDM(H0=70, Om0=0.3, Ode0=0.70, Tcmb0=0.0)
    assert allclose(cosmo.comoving_transverse_distance(redshifts), dm)
    assert allclose(cosmo.angular_diameter_distance(redshifts), da)
    assert allclose(cosmo.luminosity_distance(redshifts), dl)

    redshifts, dm, da, dl = np.loadtxt(StringIO(cosmo_open), unpack=1)
    dm = dm * u.Mpc
    da = da * u.Mpc
    dl = dl * u.Mpc
    cosmo = flrw.LambdaCDM(H0=70, Om0=0.3, Ode0=0.1, Tcmb0=0.0)
    assert allclose(cosmo.comoving_transverse_distance(redshifts), dm)
    assert allclose(cosmo.angular_diameter_distance(redshifts), da)
    assert allclose(cosmo.luminosity_distance(redshifts), dl)

    redshifts, dm, da, dl = np.loadtxt(StringIO(cosmo_closed), unpack=1)
    dm = dm * u.Mpc
    da = da * u.Mpc
    dl = dl * u.Mpc
    cosmo = flrw.LambdaCDM(H0=70, Om0=2, Ode0=0.1, Tcmb0=0.0)
    assert allclose(cosmo.comoving_transverse_distance(redshifts), dm)
    assert allclose(cosmo.angular_diameter_distance(redshifts), da)
    assert allclose(cosmo.luminosity_distance(redshifts), dl)


@pytest.mark.skipif('not HAS_SCIPY')
def test_integral():
    # Test integer vs. floating point inputs
    cosmo = flrw.LambdaCDM(H0=73.2, Om0=0.3, Ode0=0.50)
    assert allclose(cosmo.comoving_distance(3),
                    cosmo.comoving_distance(3.0), rtol=1e-7)
    assert allclose(cosmo.comoving_distance([1, 2, 3, 5]),
                    cosmo.comoving_distance([1.0, 2.0, 3.0, 5.0]),
                    rtol=1e-7)
    assert allclose(cosmo.efunc(6), cosmo.efunc(6.0), rtol=1e-7)
    assert allclose(cosmo.efunc([1, 2, 6]),
                    cosmo.efunc([1.0, 2.0, 6.0]), rtol=1e-7)
    assert allclose(cosmo.inv_efunc([1, 2, 6]),
                    cosmo.inv_efunc([1.0, 2.0, 6.0]), rtol=1e-7)


@pytest.mark.skipif('not HAS_SCIPY')
def test_de_densityscale():
    cosmo = flrw.LambdaCDM(H0=70, Om0=0.3, Ode0=0.70)
    z = np.array([0.1, 0.2, 0.5, 1.5, 2.5])
    assert allclose(cosmo.de_density_scale(z),
                    [1.0, 1.0, 1.0, 1.0, 1.0])
    # Integer check
    assert allclose(cosmo.de_density_scale(3),
                       cosmo.de_density_scale(3.0), rtol=1e-7)
    assert allclose(cosmo.de_density_scale([1, 2, 3]),
                       cosmo.de_density_scale([1., 2., 3.]), rtol=1e-7)

    cosmo = flrw.wCDM(H0=70, Om0=0.3, Ode0=0.60, w0=-0.5)
    assert allclose(cosmo.de_density_scale(z),
                    [1.15369, 1.31453, 1.83712, 3.95285, 6.5479],
                    rtol=1e-4)
    assert allclose(cosmo.de_density_scale(3),
                    cosmo.de_density_scale(3.0), rtol=1e-7)
    assert allclose(cosmo.de_density_scale([1, 2, 3]),
                    cosmo.de_density_scale([1., 2., 3.]), rtol=1e-7)

    cosmo = flrw.w0wzCDM(H0=70, Om0=0.3, Ode0=0.50, w0=-1, wz=0.5)
    assert allclose(cosmo.de_density_scale(z),
                    [0.746048, 0.5635595, 0.25712378, 0.026664129,
                     0.0035916468], rtol=1e-4)
    assert allclose(cosmo.de_density_scale(3),
                    cosmo.de_density_scale(3.0), rtol=1e-7)
    assert allclose(cosmo.de_density_scale([1, 2, 3]),
                    cosmo.de_density_scale([1., 2., 3.]), rtol=1e-7)

    cosmo = flrw.w0waCDM(H0=70, Om0=0.3, Ode0=0.70, w0=-1, wa=-0.5)
    assert allclose(cosmo.de_density_scale(z),
                    [0.9934201, 0.9767912, 0.897450,
                     0.622236, 0.4458753], rtol=1e-4)
    assert allclose(cosmo.de_density_scale(3),
                       cosmo.de_density_scale(3.0), rtol=1e-7)
    assert allclose(cosmo.de_density_scale([1, 2, 3]),
                       cosmo.de_density_scale([1., 2., 3.]), rtol=1e-7)

    cosmo = flrw.wpwaCDM(H0=70, Om0=0.3, Ode0=0.70, wp=-0.9,
                         wa=0.2, zp=0.5)
    assert allclose(cosmo.de_density_scale(z),
                    [1.012246048, 1.0280102, 1.087439,
                     1.324988, 1.565746], rtol=1e-4)
    assert allclose(cosmo.de_density_scale(3),
                    cosmo.de_density_scale(3.0), rtol=1e-7)
    assert allclose(cosmo.de_density_scale([1, 2, 3]),
                    cosmo.de_density_scale([1., 2., 3.]), rtol=1e-7)


@pytest.mark.skipif('not HAS_SCIPY')
def test_age():
    # WMAP7 but with Omega_relativisitic = 0
    tcos = flrw.FlatLambdaCDM(70.4, 0.272, Tcmb0=0.0)
    assert allclose(tcos.hubble_time, 13.889094057856937 * u.Gyr)
    assert allclose(tcos.age(4), 1.5823603508870991 * u.Gyr)
    assert allclose(tcos.age([1., 5.]),
                    [5.97113193, 1.20553129] * u.Gyr)
    assert allclose(tcos.age([1, 5]), [5.97113193, 1.20553129] * u.Gyr)

    # Add relativistic species
    tcos = flrw.FlatLambdaCDM(70.4, 0.272, Tcmb0=3.0)
    assert allclose(tcos.age(4), 1.5773003779230699 * u.Gyr)
    assert allclose(tcos.age([1, 5]), [5.96344942, 1.20093077] * u.Gyr)

    # And massive neutrinos
    tcos = flrw.FlatLambdaCDM(70.4, 0.272, Tcmb0=3.0,
                              m_nu=0.1 * u.eV)
    assert allclose(tcos.age(4), 1.5546485439853412 * u.Gyr)
    assert allclose(tcos.age([1, 5]), [5.88448152, 1.18383759] * u.Gyr)


@pytest.mark.skipif('not HAS_SCIPY')
def test_distmod():
    # WMAP7 but with Omega_relativisitic = 0
    tcos = flrw.FlatLambdaCDM(70.4, 0.272, Tcmb0=0.0)
    assert allclose(tcos.hubble_distance, 4258.415596590909 * u.Mpc)
    assert allclose(tcos.distmod([1, 5]),
                    [44.124857, 48.40167258] * u.mag)
    assert allclose(tcos.distmod([1., 5.]),
                    [44.124857, 48.40167258] * u.mag)


@pytest.mark.skipif('not HAS_SCIPY')
def test_neg_distmod():
    # Cosmology with negative luminosity distances (perfectly okay,
    #  if obscure)
    tcos = flrw.LambdaCDM(70, 0.2, 1.3, Tcmb0=0)
    assert allclose(tcos.luminosity_distance([50, 100]),
                    [16612.44047622, -46890.79092244] * u.Mpc)
    assert allclose(tcos.distmod([50, 100]),
                    [46.102167189, 48.355437790944] * u.mag)


@pytest.mark.skipif('not HAS_SCIPY')
def test_critical_density():
    from astropy.constants import codata2014

    # WMAP7 but with Omega_relativistic = 0
    # These tests will fail if astropy.const starts returning non-mks
    #  units by default; see the comment at the top of core.py.
    # critical_density0 is inversely proportional to G.
    tcos = flrw.FlatLambdaCDM(70.4, 0.272, Tcmb0=0.0)
    fac = (const.G / codata2014.G).to(u.dimensionless_unscaled).value
    assert allclose(tcos.critical_density0 * fac,
                    9.309668456020899e-30 * (u.g / u.cm**3))
    assert allclose(tcos.critical_density0,
                    tcos.critical_density(0))
    assert allclose(
        tcos.critical_density([1, 5]) * fac,
        [2.70352772e-29, 5.53739080e-28] * (u.g / u.cm**3))
    assert allclose(
        tcos.critical_density([1., 5.]) * fac,
        [2.70352772e-29, 5.53739080e-28] * (u.g / u.cm**3))


@pytest.mark.skipif('not HAS_SCIPY')
def test_comoving_distance_z1z2():
    tcos = flrw.LambdaCDM(100, 0.3, 0.8, Tcmb0=0.0)
    with pytest.raises(ValueError):  # test diff size z1, z2 fail
        tcos._comoving_distance_z1z2((1, 2), (3, 4, 5))
    # Comoving distances are invertible
    assert allclose(tcos._comoving_distance_z1z2(1, 2),
                    -tcos._comoving_distance_z1z2(2, 1))

    z1 = 0, 0, 2, 0.5, 1
    z2 = 2, 1, 1, 2.5, 1.1
    results = (3767.90579253,
               2386.25591391,
               -1381.64987862,
               2893.11776663,
               174.1524683) * u.Mpc

    assert allclose(tcos._comoving_distance_z1z2(z1, z2),
                    results)


@pytest.mark.skipif('not HAS_SCIPY')
def test_age_in_special_cosmologies():
    """Check that age in de Sitter and Einstein-de Sitter Universes work.

    Some analytic solutions fail at these critical points.
    """
    c_dS = flrw.FlatLambdaCDM(100, 0, Tcmb0=0)
    assert allclose(c_dS.age(z=0), np.inf * u.Gyr)
    assert allclose(c_dS.age(z=1), np.inf * u.Gyr)
    assert allclose(c_dS.lookback_time(z=0), 0 * u.Gyr)
    assert allclose(c_dS.lookback_time(z=1), 6.777539216261741 * u.Gyr)

    c_EdS = flrw.FlatLambdaCDM(100, 1, Tcmb0=0)
    assert allclose(c_EdS.age(z=0), 6.518614811154189 * u.Gyr)
    assert allclose(c_EdS.age(z=1), 2.3046783684542738 * u.Gyr)
    assert allclose(c_EdS.lookback_time(z=0), 0 * u.Gyr)
    assert allclose(c_EdS.lookback_time(z=1), 4.213936442699092 * u.Gyr)


@pytest.mark.skipif('not HAS_SCIPY')
def test_distance_in_special_cosmologies():
    """Check that de Sitter and Einstein-de Sitter Universes both work.

    Some analytic solutions fail at these critical points.
    """
    c_dS = flrw.FlatLambdaCDM(100, 0, Tcmb0=0)
    assert allclose(c_dS.comoving_distance(z=0), 0 * u.Mpc)
    assert allclose(c_dS.comoving_distance(z=1), 2997.92458 * u.Mpc)

    c_EdS = flrw.FlatLambdaCDM(100, 1, Tcmb0=0)
    assert allclose(c_EdS.comoving_distance(z=0), 0 * u.Mpc)
    assert allclose(c_EdS.comoving_distance(z=1), 1756.1435599923348 * u.Mpc)

    c_dS = flrw.LambdaCDM(100, 0, 1, Tcmb0=0)
    assert allclose(c_dS.comoving_distance(z=0), 0 * u.Mpc)
    assert allclose(c_dS.comoving_distance(z=1), 2997.92458 * u.Mpc)

    c_EdS = flrw.LambdaCDM(100, 1, 0, Tcmb0=0)
    assert allclose(c_EdS.comoving_distance(z=0), 0 * u.Mpc)
    assert allclose(c_EdS.comoving_distance(z=1), 1756.1435599923348 * u.Mpc)


@pytest.mark.skipif('not HAS_SCIPY')
def test_comoving_transverse_distance_z1z2():
    tcos = flrw.FlatLambdaCDM(100, 0.3, Tcmb0=0.0)
    with pytest.raises(ValueError):  # test diff size z1, z2 fail
        tcos._comoving_transverse_distance_z1z2((1, 2), (3, 4, 5))
    # Tests that should actually work, target values computed with
    # http://www.astro.multivax.de:8000/phillip/angsiz_prog/README.HTML
    # Kayser, Helbig, and Schramm (Astron.Astrophys. 318 (1997) 680-686)
    assert allclose(tcos._comoving_transverse_distance_z1z2(1, 2),
                    1313.2232194828466 * u.Mpc)

    # In a flat universe comoving distance and comoving transverse
    # distance are identical
    z1 = 0, 0, 2, 0.5, 1
    z2 = 2, 1, 1, 2.5, 1.1

    assert allclose(tcos._comoving_distance_z1z2(z1, z2),
                    tcos._comoving_transverse_distance_z1z2(z1, z2))

    # Test Flat Universe with Omega_M > 1.  Rarely used, but perfectly valid.
    tcos = flrw.FlatLambdaCDM(100, 1.5, Tcmb0=0.0)
    results = (2202.72682564,
               1559.51679971,
               -643.21002593,
               1408.36365679,
                 85.09286258) * u.Mpc

    assert allclose(tcos._comoving_transverse_distance_z1z2(z1, z2),
                    results)

    # In a flat universe comoving distance and comoving transverse
    # distance are identical
    z1 = 0, 0, 2, 0.5, 1
    z2 = 2, 1, 1, 2.5, 1.1

    assert allclose(tcos._comoving_distance_z1z2(z1, z2),
                    tcos._comoving_transverse_distance_z1z2(z1, z2))
    # Test non-flat cases to avoid simply testing
    # comoving_distance_z1z2. Test array, array case.
    tcos = flrw.LambdaCDM(100, 0.3, 0.5, Tcmb0=0.0)
    results = (3535.931375645655,
               2226.430046551708,
               -1208.6817970036532,
               2595.567367601969,
               151.36592003406884) * u.Mpc

    assert allclose(tcos._comoving_transverse_distance_z1z2(z1, z2),
                    results)

    # Test positive curvature with scalar, array combination.
    tcos = flrw.LambdaCDM(100, 1.0, 0.2, Tcmb0=0.0)
    z1 = 0.1
    z2 = 0, 0.1, 0.2, 0.5, 1.1, 2
    results = (-281.31602666724865,
               0.,
               248.58093707820436,
               843.9331377460543,
               1618.6104987686672,
               2287.5626543279927) * u.Mpc

    assert allclose(tcos._comoving_transverse_distance_z1z2(z1, z2),
                    results)


@pytest.mark.skipif('not HAS_SCIPY')
def test_angular_diameter_distance_z1z2():
    tcos = flrw.FlatLambdaCDM(70.4, 0.272, Tcmb0=0.0)
    with pytest.raises(ValueError):  # test diff size z1, z2 fail
        tcos.angular_diameter_distance_z1z2([1, 2], [3, 4, 5])
    # Tests that should actually work
    assert allclose(tcos.angular_diameter_distance_z1z2(1, 2),
                    646.22968662822018 * u.Mpc)

    z1 = 2  # Separate test for z2<z1, returns negative value with warning
    z2 = 1
    results = -969.34452994 * u.Mpc
    with pytest.warns(AstropyUserWarning, match='less than first redshift'):
        assert allclose(tcos.angular_diameter_distance_z1z2(z1, z2), results)

    z1 = 0, 0, 0.5, 1
    z2 = 2, 1, 2.5, 1.1
    results = (1760.0628637762106,
               1670.7497657219858,
               1159.0970895962193,
               115.72768186186921) * u.Mpc

    assert allclose(tcos.angular_diameter_distance_z1z2(z1, z2),
                    results)

    z1 = 0.1
    z2 = 0.1, 0.2, 0.5, 1.1, 2
    results = (0.,
               332.09893173,
               986.35635069,
               1508.37010062,
               1621.07937976) * u.Mpc
    assert allclose(tcos.angular_diameter_distance_z1z2(0.1, z2),
                    results)

    # Non-flat (positive Ok0) test
    tcos = flrw.LambdaCDM(H0=70.4, Om0=0.2, Ode0=0.5, Tcmb0=0.0)
    assert allclose(tcos.angular_diameter_distance_z1z2(1, 2),
                    620.1175337852428 * u.Mpc)
    # Non-flat (negative Ok0) test
    tcos = flrw.LambdaCDM(H0=100, Om0=2, Ode0=1, Tcmb0=0.0)
    assert allclose(tcos.angular_diameter_distance_z1z2(1, 2),
                    228.42914659246014 * u.Mpc)


@pytest.mark.skipif('not HAS_SCIPY')
def test_absorption_distance():
    tcos = flrw.FlatLambdaCDM(70.4, 0.272, Tcmb0=0.0)
    assert allclose(tcos.absorption_distance([1, 3]),
                    [1.72576635, 7.98685853])
    assert allclose(tcos.absorption_distance([1., 3.]),
                    [1.72576635, 7.98685853])
    assert allclose(tcos.absorption_distance(3), 7.98685853)
    assert allclose(tcos.absorption_distance(3.), 7.98685853)


@pytest.mark.skipif('not HAS_SCIPY')
def test_massivenu_basic():
    # Test no neutrinos case
    tcos = flrw.FlatLambdaCDM(70.4, 0.272, Neff=4.05,
                              Tcmb0=2.725 * u.K, m_nu=0)
    assert allclose(tcos.Neff, 4.05)
    assert not tcos.has_massive_nu
    mnu = tcos.m_nu
    assert len(mnu) == 4
    assert mnu.unit == u.eV
    assert allclose(mnu, [0.0, 0.0, 0.0, 0.0] * u.eV)
    assert allclose(tcos.nu_relative_density(1.), 0.22710731766 * 4.05,
                    rtol=1e-6)
    assert allclose(tcos.nu_relative_density(1), 0.22710731766 * 4.05,
                    rtol=1e-6)

    # Alternative no neutrinos case
    tcos = flrw.FlatLambdaCDM(70.4, 0.272, Tcmb0=0 * u.K,
                              m_nu=str((0.4 * u.eV).to(u.g, u.mass_energy())))
    assert not tcos.has_massive_nu
    assert tcos.m_nu is None

    # Test basic setting, retrieval of values
    tcos = flrw.FlatLambdaCDM(70.4, 0.272, Tcmb0=2.725 * u.K,
                              m_nu=u.Quantity([0.0, 0.01, 0.02], u.eV))
    assert tcos.has_massive_nu
    mnu = tcos.m_nu
    assert len(mnu) == 3
    assert mnu.unit == u.eV
    assert allclose(mnu, [0.0, 0.01, 0.02] * u.eV)

    # All massive neutrinos case
    tcos = flrw.FlatLambdaCDM(70.4, 0.272, Tcmb0=2.725,
                              m_nu=u.Quantity(0.1, u.eV), Neff=3.1)
    assert allclose(tcos.Neff, 3.1)
    assert tcos.has_massive_nu
    mnu = tcos.m_nu
    assert len(mnu) == 3
    assert mnu.unit == u.eV
    assert allclose(mnu, [0.1, 0.1, 0.1] * u.eV)


@pytest.mark.skipif('not HAS_SCIPY')
def test_distances():
    # Test distance calculations for various special case
    #  scenarios (no relativistic species, normal, massive neutrinos)
    # These do not come from external codes -- they are just internal
    #  checks to make sure nothing changes if we muck with the distance
    #  calculators

    z = np.array([1.0, 2.0, 3.0, 4.0])

    # The pattern here is: no relativistic species, the relativistic
    # species with massless neutrinos, then massive neutrinos
    cos = flrw.LambdaCDM(75.0, 0.25, 0.5, Tcmb0=0.0)
    assert allclose(cos.comoving_distance(z),
                    [2953.93001902, 4616.7134253, 5685.07765971,
                     6440.80611897] * u.Mpc, rtol=1e-4)
    cos = flrw.LambdaCDM(75.0, 0.25, 0.6, Tcmb0=3.0, Neff=3,
                         m_nu=u.Quantity(0.0, u.eV))
    assert allclose(cos.comoving_distance(z),
                    [3037.12620424, 4776.86236327, 5889.55164479,
                     6671.85418235] * u.Mpc, rtol=1e-4)
    cos = flrw.LambdaCDM(75.0, 0.3, 0.4, Tcmb0=3.0, Neff=3,
                         m_nu=u.Quantity(10.0, u.eV))
    assert allclose(cos.comoving_distance(z),
                    [2471.80626824, 3567.1902565, 4207.15995626,
                     4638.20476018] * u.Mpc, rtol=1e-4)
    # Flat
    cos = flrw.FlatLambdaCDM(75.0, 0.25, Tcmb0=0.0)
    assert allclose(cos.comoving_distance(z),
                    [3180.83488552, 5060.82054204, 6253.6721173,
                     7083.5374303] * u.Mpc, rtol=1e-4)
    cos = flrw.FlatLambdaCDM(75.0, 0.25, Tcmb0=3.0, Neff=3,
                              m_nu=u.Quantity(0.0, u.eV))
    assert allclose(cos.comoving_distance(z),
                    [3180.42662867, 5059.60529655, 6251.62766102,
                     7080.71698117] * u.Mpc, rtol=1e-4)
    cos = flrw.FlatLambdaCDM(75.0, 0.25, Tcmb0=3.0, Neff=3,
                              m_nu=u.Quantity(10.0, u.eV))
    assert allclose(cos.comoving_distance(z),
                    [2337.54183142, 3371.91131264, 3988.40711188,
                     4409.09346922] * u.Mpc, rtol=1e-4)
    # Add w
    cos = flrw.FlatwCDM(75.0, 0.25, w0=-1.05, Tcmb0=0.0)
    assert allclose(cos.comoving_distance(z),
                    [3216.8296894, 5117.2097601, 6317.05995437,
                     7149.68648536] * u.Mpc, rtol=1e-4)
    cos = flrw.FlatwCDM(75.0, 0.25, w0=-0.95, Tcmb0=3.0, Neff=3,
                    m_nu=u.Quantity(0.0, u.eV))
    assert allclose(cos.comoving_distance(z),
                    [3143.56537758, 5000.32196494, 6184.11444601,
                     7009.80166062] * u.Mpc, rtol=1e-4)
    cos = flrw.FlatwCDM(75.0, 0.25, w0=-0.9, Tcmb0=3.0, Neff=3,
                    m_nu=u.Quantity(10.0, u.eV))
    assert allclose(cos.comoving_distance(z),
                    [2337.76035371, 3372.1971387, 3988.71362289,
                     4409.40817174] * u.Mpc, rtol=1e-4)
    # Non-flat w
    cos = flrw.wCDM(75.0, 0.25, 0.4, w0=-0.9, Tcmb0=0.0)
    assert allclose(cos.comoving_distance(z),
                    [2849.6163356, 4428.71661565, 5450.97862778,
                     6179.37072324] * u.Mpc, rtol=1e-4)
    cos = flrw.wCDM(75.0, 0.25, 0.4, w0=-1.1, Tcmb0=3.0, Neff=3,
                    m_nu=u.Quantity(0.0, u.eV))
    assert allclose(cos.comoving_distance(z),
                    [2904.35580229, 4511.11471267, 5543.43643353,
                     6275.9206788] * u.Mpc, rtol=1e-4)
    cos = flrw.wCDM(75.0, 0.25, 0.4, w0=-0.9, Tcmb0=3.0, Neff=3,
                    m_nu=u.Quantity(10.0, u.eV))
    assert allclose(cos.comoving_distance(z),
                    [2473.32522734, 3581.54519631, 4232.41674426,
                     4671.83818117] * u.Mpc, rtol=1e-4)
    # w0wa
    cos = flrw.w0waCDM(75.0, 0.3, 0.6, w0=-0.9, wa=0.1, Tcmb0=0.0)
    assert allclose(cos.comoving_distance(z),
                    [2937.7807638, 4572.59950903, 5611.52821924,
                     6339.8549956] * u.Mpc, rtol=1e-4)
    cos = flrw.w0waCDM(75.0, 0.25, 0.5, w0=-0.9, wa=0.1, Tcmb0=3.0, Neff=3,
                       m_nu=u.Quantity(0.0, u.eV))
    assert allclose(cos.comoving_distance(z),
                    [2907.34722624, 4539.01723198, 5593.51611281,
                     6342.3228444] * u.Mpc, rtol=1e-4)
    cos = flrw.w0waCDM(75.0, 0.25, 0.5, w0=-0.9, wa=0.1, Tcmb0=3.0, Neff=3,
                       m_nu=u.Quantity(10.0, u.eV))
    assert allclose(cos.comoving_distance(z),
                    [2507.18336722, 3633.33231695, 4292.44746919,
                     4736.35404638] * u.Mpc, rtol=1e-4)
    # Flatw0wa
    cos = flrw.Flatw0waCDM(75.0, 0.25, w0=-0.95, wa=0.15, Tcmb0=0.0)
    assert allclose(cos.comoving_distance(z),
                    [3123.29892781, 4956.15204302, 6128.15563818,
                     6948.26480378] * u.Mpc, rtol=1e-4)
    cos = flrw.Flatw0waCDM(75.0, 0.25, w0=-0.95, wa=0.15, Tcmb0=3.0, Neff=3,
                           m_nu=u.Quantity(0.0, u.eV))
    assert allclose(cos.comoving_distance(z),
                    [3122.92671907, 4955.03768936, 6126.25719576,
                     6945.61856513] * u.Mpc, rtol=1e-4)
    cos = flrw.Flatw0waCDM(75.0, 0.25, w0=-0.95, wa=0.15, Tcmb0=3.0, Neff=3,
                           m_nu=u.Quantity(10.0, u.eV))
    assert allclose(cos.comoving_distance(z),
                    [2337.70072701, 3372.13719963, 3988.6571093,
                     4409.35399673] * u.Mpc, rtol=1e-4)
    # wpwa
    cos = flrw.wpwaCDM(75.0, 0.3, 0.6, wp=-0.9, zp=0.5, wa=0.1, Tcmb0=0.0)
    assert allclose(cos.comoving_distance(z),
                    [2954.68975298, 4599.83254834, 5643.04013201,
                     6373.36147627] * u.Mpc, rtol=1e-4)
    cos = flrw.wpwaCDM(75.0, 0.25, 0.5, wp=-0.9, zp=0.4, wa=0.1,
                       Tcmb0=3.0, Neff=3, m_nu=u.Quantity(0.0, u.eV))
    assert allclose(cos.comoving_distance(z),
                    [2919.00656215, 4558.0218123, 5615.73412391,
                     6366.10224229] * u.Mpc, rtol=1e-4)
    cos = flrw.wpwaCDM(75.0, 0.25, 0.5, wp=-0.9, zp=1.0, wa=0.1, Tcmb0=3.0,
                       Neff=4, m_nu=u.Quantity(5.0, u.eV))
    assert allclose(cos.comoving_distance(z),
                    [2629.48489827, 3874.13392319, 4614.31562397,
                     5116.51184842] * u.Mpc, rtol=1e-4)

    # w0wz
    cos = flrw.w0wzCDM(75.0, 0.3, 0.6, w0=-0.9, wz=0.1, Tcmb0=0.0)
    assert allclose(cos.comoving_distance(z),
                    [3051.68786716, 4756.17714818, 5822.38084257,
                     6562.70873734] * u.Mpc, rtol=1e-4)
    cos = flrw.w0wzCDM(75.0, 0.25, 0.5, w0=-0.9, wz=0.1,
                       Tcmb0=3.0, Neff=3, m_nu=u.Quantity(0.0, u.eV))
    assert allclose(cos.comoving_distance(z),
                    [2997.8115653, 4686.45599916, 5764.54388557,
                     6524.17408738] * u.Mpc, rtol=1e-4)
    cos = flrw.w0wzCDM(75.0, 0.25, 0.5, w0=-0.9, wz=0.1, Tcmb0=3.0,
                       Neff=4, m_nu=u.Quantity(5.0, u.eV))
    assert allclose(cos.comoving_distance(z),
                    [2676.73467639, 3940.57967585, 4686.90810278,
                     5191.54178243] * u.Mpc, rtol=1e-4)

    # Also test different numbers of massive neutrinos
    # for FlatLambdaCDM to give the scalar nu density functions a
    # work out
    cos = flrw.FlatLambdaCDM(75.0, 0.25, Tcmb0=3.0,
                             m_nu=u.Quantity([10.0, 0, 0], u.eV))
    assert allclose(cos.comoving_distance(z),
                    [2777.71589173, 4186.91111666, 5046.0300719,
                     5636.10397302] * u.Mpc, rtol=1e-4)
    cos = flrw.FlatLambdaCDM(75.0, 0.25, Tcmb0=3.0,
                             m_nu=u.Quantity([10.0, 5, 0], u.eV))
    assert allclose(cos.comoving_distance(z),
                    [2636.48149391, 3913.14102091, 4684.59108974,
                     5213.07557084] * u.Mpc, rtol=1e-4)
    cos = flrw.FlatLambdaCDM(75.0, 0.25, Tcmb0=3.0,
                             m_nu=u.Quantity([4.0, 5, 9], u.eV))
    assert allclose(cos.comoving_distance(z),
                    [2563.5093049, 3776.63362071, 4506.83448243,
                     5006.50158829] * u.Mpc, rtol=1e-4)
    cos = flrw.FlatLambdaCDM(75.0, 0.25, Tcmb0=3.0, Neff=4.2,
                             m_nu=u.Quantity([1.0, 4.0, 5, 9], u.eV))
    assert allclose(cos.comoving_distance(z),
                    [2525.58017482, 3706.87633298, 4416.58398847,
                     4901.96669755] * u.Mpc, rtol=1e-4)


@pytest.mark.skipif('not HAS_SCIPY')
def test_massivenu_density():
    # Testing neutrino density calculation

    # Simple test cosmology, where we compare rho_nu and rho_gamma
    # against the exact formula (eq 24/25 of Komatsu et al. 2011)
    # computed using Mathematica.  The approximation we use for f(y)
    # is only good to ~ 0.5% (with some redshift dependence), so that's
    # what we test to.
    ztest = np.array([0.0, 1.0, 2.0, 10.0, 1000.0])
    nuprefac = 7.0 / 8.0 * (4.0 / 11.0) ** (4.0 / 3.0)
    #  First try 3 massive neutrinos, all 100 eV -- note this is a universe
    #  seriously dominated by neutrinos!
    tcos = flrw.FlatLambdaCDM(75.0, 0.25, Tcmb0=3.0, Neff=3,
                              m_nu=u.Quantity(100.0, u.eV))
    assert tcos.has_massive_nu
    assert tcos.Neff == 3
    nurel_exp = nuprefac * tcos.Neff * np.array([171969, 85984.5, 57323,
                                                 15633.5, 171.801])
    assert allclose(tcos.nu_relative_density(ztest), nurel_exp, rtol=5e-3)
    assert allclose(tcos.efunc([0.0, 1.0]), [1.0, 7.46144727668], rtol=5e-3)

    # Next, slightly less massive
    tcos = flrw.FlatLambdaCDM(75.0, 0.25, Tcmb0=3.0, Neff=3,
                              m_nu=u.Quantity(0.25, u.eV))
    nurel_exp = nuprefac * tcos.Neff * np.array([429.924, 214.964, 143.312,
                                                 39.1005, 1.11086])
    assert allclose(tcos.nu_relative_density(ztest), nurel_exp,
                       rtol=5e-3)

    # For this one also test Onu directly
    onu_exp = np.array([0.01890217, 0.05244681, 0.0638236,
                        0.06999286, 0.1344951])
    assert allclose(tcos.Onu(ztest), onu_exp, rtol=5e-3)

    # And fairly light
    tcos = flrw.FlatLambdaCDM(80.0, 0.30, Tcmb0=3.0, Neff=3,
                              m_nu=u.Quantity(0.01, u.eV))

    nurel_exp = nuprefac * tcos.Neff * np.array([17.2347, 8.67345, 5.84348,
                                                 1.90671, 1.00021])
    assert allclose(tcos.nu_relative_density(ztest), nurel_exp,
                    rtol=5e-3)
    onu_exp = np.array([0.00066599, 0.00172677, 0.0020732,
                        0.00268404, 0.0978313])
    assert allclose(tcos.Onu(ztest), onu_exp, rtol=5e-3)
    assert allclose(tcos.efunc([1.0, 2.0]), [1.76225893, 2.97022048],
                    rtol=1e-4)
    assert allclose(tcos.inv_efunc([1.0, 2.0]), [0.5674535, 0.33667534],
                    rtol=1e-4)

    # Now a mixture of neutrino masses, with non-integer Neff
    tcos = flrw.FlatLambdaCDM(80.0, 0.30, Tcmb0=3.0, Neff=3.04,
                              m_nu=u.Quantity([0.0, 0.01, 0.25], u.eV))
    nurel_exp = nuprefac * tcos.Neff * \
                np.array([149.386233, 74.87915, 50.0518,
                          14.002403, 1.03702333])
    assert allclose(tcos.nu_relative_density(ztest), nurel_exp,
                    rtol=5e-3)
    onu_exp = np.array([0.00584959, 0.01493142, 0.01772291,
                        0.01963451, 0.10227728])
    assert allclose(tcos.Onu(ztest), onu_exp, rtol=5e-3)

    # Integer redshifts
    ztest = ztest.astype(int)
    assert allclose(tcos.nu_relative_density(ztest), nurel_exp,
                    rtol=5e-3)
    assert allclose(tcos.Onu(ztest), onu_exp, rtol=5e-3)


@pytest.mark.skipif('not HAS_SCIPY')
def test_elliptic_comoving_distance_z1z2():
    """Regression test for #8388."""
    cosmo = flrw.LambdaCDM(70., 2.3, 0.05, Tcmb0=0)
    z = 0.2
    assert allclose(cosmo.comoving_distance(z),
                    cosmo._integral_comoving_distance_z1z2(0., z))
    assert allclose(cosmo._elliptic_comoving_distance_z1z2(0., z),
                    cosmo._integral_comoving_distance_z1z2(0., z))


SPECIALIZED_COMOVING_DISTANCE_COSMOLOGIES = [
    flrw.FlatLambdaCDM(H0=70, Om0=0.0, Tcmb0=0.0),  # de Sitter
    flrw.FlatLambdaCDM(H0=70, Om0=1.0, Tcmb0=0.0),  # Einstein - de Sitter
    flrw.FlatLambdaCDM(H0=70, Om0=0.3, Tcmb0=0.0),  # Hypergeometric
    flrw.LambdaCDM(H0=70, Om0=0.3, Ode0=0.6, Tcmb0=0.0),  # Elliptic
]


ITERABLE_REDSHIFTS = [
    (0, 1, 2, 3, 4),  # tuple
    [0, 1, 2, 3, 4],  # list
    np.array([0, 1, 2, 3, 4]),  # array
]


@pytest.mark.skipif('not HAS_SCIPY')
@pytest.mark.parametrize('cosmo', SPECIALIZED_COMOVING_DISTANCE_COSMOLOGIES)
@pytest.mark.parametrize('z', ITERABLE_REDSHIFTS)
def test_comoving_distance_iterable_argument(cosmo, z):
    """
    Regression test for #10980
    Test that specialized comoving distance methods handle iterable arguments.
    """

    assert allclose(cosmo.comoving_distance(z),
                    cosmo._integral_comoving_distance_z1z2(0., z))


@pytest.mark.skipif('not HAS_SCIPY')
@pytest.mark.parametrize('cosmo', SPECIALIZED_COMOVING_DISTANCE_COSMOLOGIES)
def test_comoving_distance_broadcast(cosmo):
    """
    Regression test for #10980
    Test that specialized comoving distance methods broadcast array arguments.
    """

    z1 = np.zeros((2, 5))
    z2 = np.ones((3, 1, 5))
    z3 = np.ones((7, 5))
    output_shape = np.broadcast(z1, z2).shape

    # Check compatible array arguments return an array with the correct shape
    assert cosmo._comoving_distance_z1z2(z1, z2).shape == output_shape

    # Check incompatible array arguments raise an error
    with pytest.raises(ValueError, match='z1 and z2 have different shapes'):
        cosmo._comoving_distance_z1z2(z1, z3)
