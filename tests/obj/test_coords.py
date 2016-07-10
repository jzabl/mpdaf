"""Test on WCS and WaveCoord objects."""

from __future__ import absolute_import, division

import nose.tools
import pytest

import astropy.units as u
import numpy as np
from astropy import wcs as pywcs
from astropy.io import fits
from mpdaf.obj import WCS, WaveCoord, deg2sexa, sexa2deg, determine_refframe
from numpy.testing import assert_allclose, assert_array_equal


class TestWCS(object):

    def test_from_hdr(self):
        """WCS class: testing constructor """
        h = fits.getheader('data/obj/a370II.fits')
        wcs = WCS(h)
        h2 = wcs.to_header()
        wcs2 = WCS(h2)
        wcs2.naxis1 = wcs.naxis1
        wcs2.naxis2 = wcs.naxis2
        assert wcs.isEqual(wcs2)

    def test_from_hdr2(self):
        """WCS class: testing constructor 2 """
        h = fits.open('data/sdetect/a478hst-cutout.fits')
        frame, equinox = determine_refframe(h[0].header)
        wcs = WCS(h[1].header, frame=frame, equinox=equinox)
        nose.tools.assert_equal(wcs.wcs.wcs.equinox, 2000.0)
        nose.tools.assert_equal(wcs.wcs.wcs.radesys, 'FK5')

    def test_copy(self):
        """WCS class: tests copy"""
        wcs = WCS(crval=(0, 0), shape=(5, 6))
        wcs2 = wcs.copy()
        assert wcs.isEqual(wcs2)

    def test_coordTransform(self):
        """WCS class: testing coordinates transformations"""
        wcs = WCS(crval=(0, 0), shape=(5, 6))
        pixcrd = [[0, 0], [2, 3], [3, 2]]
        pixsky = wcs.pix2sky(pixcrd)
        pixcrd2 = wcs.sky2pix(pixsky)
        assert_array_equal(pixcrd, pixcrd2)

    def test_coordTransform2(self):
        """WCS class: testing transformations with a more complete header."""

        w = pywcs.WCS(naxis=2)
        w.wcs.crpix = [167.401033093, 163.017401336]
        w.wcs.cd = np.array([[-5.5555555555555003e-05, 0],
                             [0, 5.5555555555555003e-05]])
        w.wcs.crval = [338.23092027, -60.56375796]
        w.wcs.ctype = ["RA---TAN", "DEC--TAN"]

        wcs = WCS()
        wcs.wcs = w

        pix = np.array([[108.41, 81.34]])
        pix2 = pix[:, [1, 0]]
        pixint = pix2.astype(int)
        ref = np.array([[338.2375, -60.5682]])
        ref2 = ref[:, [1, 0]]
        sky = wcs.pix2sky(pix2)

        assert_allclose(wcs.wcs.wcs_pix2world(pix, 0), ref, rtol=1e-4)
        assert_allclose(sky, ref2, rtol=1e-4)
        assert_allclose(wcs.sky2pix(wcs.pix2sky(pix2)), pix2)
        assert_allclose(wcs.sky2pix(sky, nearest=True), pixint)

    def test_get(self):
        """WCS class: testing getters"""
        wcs = WCS(crval=(0, 0), shape=(5, 6), crpix=(1, 1))
        assert_array_equal(wcs.get_step(), [1.0, 1.0])
        assert_array_equal(wcs.get_start(), [0.0, 0.0])
        assert_array_equal(wcs.get_end(), [4.0, 5.0])

        wcs2 = WCS(crval=(0, 0), shape=(5, 6))
        assert_array_equal(wcs2.get_step(), [1.0, 1.0])
        assert_array_equal(wcs2.get_start(), [-2.0, -2.5])
        assert_array_equal(wcs2.get_end(), [2.0, 2.5])

        wcs2.set_step([0.5, 2.5])
        assert_array_equal(wcs2.get_step(), [0.5, 2.5])

        wcs2.set_crval2(-2, unit=2 * u.pix)
        assert_array_equal(wcs2.get_crval2(), -4.0)


class TestWaveCoord(object):

    def test_from_hdr(self):
        """WaveCoord class: testing constructor """
        h = fits.getheader('data/obj/Spectrum_Novariance.fits')
        wave = WaveCoord(h)
        h2 = wave.to_header()
        wave2 = WaveCoord(h2)
        wave2.shape = wave.shape
        assert wave.isEqual(wave2)

    def test_copy(self):
        """WaveCoord class: testing copy"""
        wave = WaveCoord(crval=0, cunit=u.nm, shape=10)
        wave2 = wave.copy()
        assert wave.isEqual(wave2)

    def test_coord_transform(self):
        """WaveCoord class: testing coordinates transformations"""
        wave = WaveCoord(crval=0, cunit=u.nm, shape=10)
        pixel = wave.pixel(wave.coord(5, unit=u.nm), nearest=True, unit=u.nm)
        nose.tools.assert_equal(pixel, 5)

        wave2 = np.arange(10)
        pixel = wave.pixel(wave.coord(wave2, unit=u.nm), nearest=True,
                           unit=u.nm)
        np.testing.assert_array_equal(pixel, wave2)

        pix = np.arange(wave.shape, dtype=np.float)
        np.testing.assert_allclose(wave.pixel(wave.coord(unit=u.nm),
                                              unit=u.nm), pix)

    def test_get(self):
        """WaveCoord class: testing getters"""
        wave = WaveCoord(crval=0, cunit=u.nm, shape=10)
        nose.tools.assert_equal(wave.get_step(unit=u.nm), 1.0)
        nose.tools.assert_equal(wave.get_start(unit=u.nm), 0.0)
        nose.tools.assert_equal(wave.get_end(unit=u.nm), 9.0)

    def test_rebin(self):
        """WCS class: testing rebin method"""
        wave = WaveCoord(crval=0, cunit=u.nm, shape=10)
        wave.rebin(factor=2)
        nose.tools.assert_equal(wave.get_step(unit=u.nm), 2.0)
        nose.tools.assert_equal(wave.get_start(unit=u.nm), 0.5)
        nose.tools.assert_equal(wave.coord(2, unit=u.nm), 4.5)
        nose.tools.assert_equal(wave.shape, 5)

    def test_resample(self):
        """WCS class: testing resampling method"""
        wave = WaveCoord(crval=0, cunit=u.nm, shape=10)
        wave2 = wave.resample(step=2.5, start=20, unit=u.angstrom)
        nose.tools.assert_equal(wave2.get_step(unit=u.nm), 0.25)
        nose.tools.assert_equal(wave2.get_start(unit=u.nm), 2.0)
        nose.tools.assert_equal(wave2.shape, 32)

    def test_muse_header(self):
        """WCS class: testing MUSE header specifities."""
        d = dict(crval=4750., crpix=1., ctype='AWAV', cdelt=1.25,
                 cunit=u.angstrom, shape=3681)
        wave = WaveCoord(**d)
        start = d['crval']
        end = d['crval'] + d['cdelt'] * (d['shape'] - 1)
        nose.tools.assert_equal(wave.get_step(), d['cdelt'])
        nose.tools.assert_equal(wave.get_crval(), start)
        nose.tools.assert_equal(wave.get_start(), start)
        nose.tools.assert_equal(wave.get_end(), end)
        assert_array_equal(wave.get_range(), [start, end])
        nose.tools.assert_equal(wave.get_crpix(), d['crpix'])
        nose.tools.assert_equal(wave.get_ctype(), d['ctype'])

        def to_nm(val):
            return (val * u.angstrom).to(u.nm).value
        nose.tools.assert_equal(wave.get_step(u.nm), to_nm(d['cdelt']))
        nose.tools.assert_equal(wave.get_crval(u.nm), to_nm(start))
        nose.tools.assert_equal(wave.get_start(u.nm), to_nm(start))
        nose.tools.assert_equal(wave.get_end(u.nm), to_nm(end))
        assert_array_equal(wave.get_range(u.nm), [to_nm(start), to_nm(end)])


def test_deg_sexa():
    """testing degree/sexagesimal transformations"""
    ra = '23:51:41.268'
    dec = '-26:04:43.032'

    deg = sexa2deg([dec, ra])
    assert_allclose(deg, (-26.07862, 357.92195), atol=1e-3)
    deg = sexa2deg([[dec, ra]])[0]
    assert_allclose(deg, (-26.07862, 357.92195), atol=1e-3)

    sexa = deg2sexa([-26.07862, 357.92195])
    assert_array_equal(sexa, (dec, ra))
    sexa = deg2sexa([[-26.07862, 357.92195]])[0]
    assert_array_equal(sexa, (dec, ra))


def test_determine_refframe():
    nose.tools.assert_equal(determine_refframe({'EQUINOX': 2000.})[0], 'FK5')
    nose.tools.assert_equal(determine_refframe({'EQUINOX': 2000.,
                                                'RADESYS': 'FK5'})[0], 'FK5')
    nose.tools.assert_equal(determine_refframe({'RADESYS': 'FK5'})[0], 'FK5')
    nose.tools.assert_equal(determine_refframe({'RADECSYS': 'FK5'})[0], 'FK5')
    nose.tools.assert_equal(determine_refframe({'RADESYS': 'ICRS'})[0], 'ICRS')
    nose.tools.assert_equal(determine_refframe({})[0], None)
