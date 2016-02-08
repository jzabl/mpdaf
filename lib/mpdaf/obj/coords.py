"""coords.py Manages coordinates."""

from astropy.coordinates import Angle
from astropy.io import fits
import astropy.units as u
import astropy.wcs as pywcs
import logging
import numpy as np

from .objs import is_float, is_int
from ..tools import fix_unit_read


def deg2sexa(x):
    """Transform one or more equatorial coordinate pairs from
       degrees to sexagesimal strings.

    Parameters
    ----------
    x : float array
        Either a single coordinate in a 1D array like [dec,ra],
        or a 2D array of multiple (dec,ra) coordinates, ordered like
        [[dec1,ra1], [dec2,ra2], ...].  All coordinates must be in
        degrees.

    Returns
    -------
    out : array of strings
          The array of dec,ra coordinates as sexagesimal strings,
          stored in an array of the same dimensions as the input
          array. Declination values are written like
          degrees:minutes:seconds. Right-ascension values are
          written like hours:minutes:seconds.

    """
    x = np.array(x)

    # Is this a single-dimensional array containing a single ra,dec
    # coordinate like [ra,dec]?

    if len(np.shape(x)) == 1 and np.shape(x)[0] == 2:
        ra = deg2hms(x[1])
        dec = deg2dms(x[0])
        return np.array([dec, ra])

    # Or is this a 2D array of multiple [ra,dec] coordinates?

    elif len(np.shape(x)) == 2 and np.shape(x)[1] == 2:
        result = []
        for i in range(np.shape(x)[0]):
            ra = deg2hms(x[i][1])
            dec = deg2dms(x[i][0])
            result.append(np.array([dec, ra]))
        return np.array(result)
    else:
        raise ValueError('Operation forbidden')


def sexa2deg(x):
    """Transform one or more equatorial coordinate pairs from
       sexagesimal strings to decimal degrees.

    Parameters
    ----------
    x : string array
        Either a single pair of coordinate strings in a 1D array like
        [dec,ra], or a 2D array of multiple (dec,ra) coordinate
        strings, ordered like [[dec1,ra1], [dec2,ra2], ...]. In each
        coordinate pair, the declination string should be written like
        degrees:minutes:seconds, and the right-ascension string should
        be written like hours:minutes:seconds.

    Returns
    -------
    out : array of numbers
          The array of ra,dec coordinates in degrees, returned in an
          array of the same dimensions as the input array.

    """
    x = np.array(x)

    # Is this a single-dimensional array containing a single ra,dec
    # coordinate like [ra,dec]?

    if len(np.shape(x)) == 1 and np.shape(x)[0] == 2:
        ra = hms2deg(x[1])
        dec = dms2deg(x[0])
        return np.array([dec, ra])

    # Or is this a 2D array of multiple [ra,dec] coordinates?

    elif len(np.shape(x)) == 2 and np.shape(x)[1] == 2:
        result = []
        for i in range(np.shape(x)[0]):
            ra = hms2deg(x[i][1])
            dec = dms2deg(x[i][0])
            result.append(np.array([dec, ra]))
        return np.array(result)
    else:
        raise ValueError('Operation forbidden')


def deg2hms(x):
    """Transform a degree value to a string representation
    of the coordinate as hours:minutes:seconds.

    Parameters
    ----------
    x : float
        The degree value to be written as a sexagesimal string.

    Returns
    -------
    out : string
        The input angle written as a sexagesimal string, in the
        form, hours:minutes:seconds.

    """
    ac = Angle(x, unit='degree')
    hms = ac.to_string(unit='hour', sep=':', pad=True)
    return str(hms)


def hms2deg(x):
    """Transform a string representation of a coordinate,
    written as hours:minutes:seconds, to a float degree value.

    Parameters
    ----------
    x : string
        The input angle, written in the form, hours:minutes:seconds

    Returns
    -------
    out : float
        The angle as a number of degrees.

    """
    ac = Angle(x, unit='hour')
    deg = float(ac.to_string(unit='degree', decimal=True))
    return deg


def deg2dms(x):
    """Transform a degree value to a string representation
       of the coordinate, written as degrees:arcminutes:arcseconds.

    Parameters
    ----------
    x : float
        The degree value to be converted.

    Returns
    -------
    out : string
        The input angle as a string, written as degrees:minutes:seconds.
    """
    ac = Angle(x, unit='degree')
    dms = ac.to_string(unit='degree', sep=':', pad=True)
    return str(dms)


def dms2deg(x):
    """Transform a string representation of the coordinate,
       written as degrees:arcminutes:arcseconds, to a float degree value.

    Parameters
    ----------
    x : string
        The input angle written in the form, degrees:arcminutes:arcseconds

    Returns
    -------
    out : float
        The input angle as a number of degrees.

    """
    ac = Angle(x, unit='degree')
    deg = float(ac.to_string(unit='degree', decimal=True))
    return deg


def wcs_from_header(hdr, naxis=None):
    if 'CD1_1' in hdr and 'CDELT3' in hdr and 'CD3_3' not in hdr:
        hdr['CD3_3'] = hdr['CDELT3']
    if 'PC1_1' in hdr and 'CDELT3' in hdr and 'PC3_3' not in hdr:
        hdr['PC3_3'] = 1
    # WCS object from data header
    return pywcs.WCS(hdr, naxis=naxis)


class WCS(object):

    """The WCS class manages the world coordinates of the spatial axes of
    MPDAF images, using the pywcs package.

    Note that MPDAF images are stored in python arrays that are
    indexed in [y,x] axis order. In general the axes of these arrays
    are not along celestial axes such as right-ascension and
    declination. They are cartesian axes of a flat map projection of
    the sky around the observation center, and they may be rotated
    away from the celestial axes. When their rotation angle is zero,
    the Y axis is parallel to the declination axis. However the X axis
    is only along the right ascension axis for observations at zero
    declination.

    Pixels in MPDAF images are not generally square on the sky. To
    scale index offsets in the image to angular distances in the map
    projection, the Y-axis and X-axis index offsets must be scaled by
    different numbers. These numbers can be obtained by calling the
    get_step() method, which returns the angular increments per pixel
    along the Y and X axes of the array. The Y-axis increment is
    always positive, but the X-axis increment is negative if east is
    anti-clockwise of north when the X-axis pixels are plotted from
    left to right,

    The rotation angle of the map projection, relative to the sky, can
    be obtained by calling the get_rot() method. This returns the
    angle between celestial north and the Y axis of the image, in the
    sense of an eastward rotation of celestial north from the Y-axis.

    When the linearized coordinates of the map projection are
    insufficient, the celestial coordinates of one or more pixels can
    be queried by calling the pix2sky() method, which returns
    coordinates in the [dec,ra] axis order. In the other direction,
    the [y,x] indexes of the pixel of a given celestial coordinate can
    be obtained by calling the sky2pix() method.

    Parameters
    ----------
    hdr : astropy.fits.CardList
        A FITS header. If the hdr parameter is not None, the WCS
        object is created from the data header, and the remaining
        parameters are ignored.
    crpix : float or (float,float)
        The FITS array indexes of the reference pixel of the image,
        given in the order (y,x). Note that the first pixel of the
        FITS image is [1,1], whereas in the python image array it is
        [0,0]. Thus to place the reference pixel at [ry,rx] in the
        python image array would require crpix=(ry+1,rx+1).

        If both crpix and shape are None, then crpix is given the
        value (1.0,1.0) and the reference position is at index [0,0]
        in the python array of the image.

        If crpix is None and shape is not None, then crpix is set to
        (shape + 1.0)/2.0, which places the reference point at the
        center of the image.
    crval : float or (float,float)
        The celestial coordinates of the reference pixel
        (ref_dec,ref_ra). If this paramater is not provided, then
        (0.0,0.0) is substituted.
    cdelt : float or (float,float)
        If the hdr and cd parameters are both None, then this argument
        can be used to specify the pixel increments along the Y and X
        axes of the image, respectively.  If this parameter is not
        provided, (1.0,1.0) is substituted. Note that it is
        conventional for cdelt[1] to be negative, such that east is
        plotted towards the left when the image rotation angle is
        zero.
    deg : bool
        If True, then cdelt and crval are in decimal degrees
        (CTYPE1='RA---TAN',CTYPE2='DEC--TAN',CUNIT1=CUNIT2='deg').
        If False (the default), the celestial coordinates are linear
        (CTYPE1=CTYPE2='LINEAR').
    rot : float
        If the hdr and cd paramters are both None, then this argument
        can be used to specify a value for the rotation angle of the
        image. This is the angle between celestial north and the Y
        axis of the image, in the sense of an eastward rotation of
        celestial north from the Y-axis.

        Along with the cdelt parameter, the rot parameter is used to
        construct a FITS CD rotation matrix. This is done as described
        in equation 189 of Calabretta, M. R., and Greisen, E. W,
        Astronomy & Astrophysics, 395, 1077-1122, 2002, where it
        serves as the value of the CROTA term.
    shape : integer or (integer,integer)
        The dimensions of the image axes (optional). The dimensions
        are given in python order (ny,nx).
    cd : numpy.ndarray
         This parameter can optionally be used to specify the FITS CD
         rotation matrix. By default this parameter is None. However if
         a matrix is provided and hdr is None, then it is used
         instead of cdelt and rot, which are then ignored. The matrix
         should be ordered like

           cd = numpy.array([[CD1_1, CD1_2],
                             [CD2_1, CD2_2]]),

         where CDj_i are the names of the corresponding FITS keywords.

    Attributes
    ----------
    wcs : pywcs.WCS
        The underlying object that performs most of the world coordinate
        conversions.

    """

    def __init__(self, hdr=None, crpix=None, crval=(1.0, 1.0),
                 cdelt=(1.0, 1.0), deg=False, rot=0, shape=None, cd=None):
        self._logger = logging.getLogger(__name__)

        # Initialize the WCS object from a FITS header?
        # If so, also keep a record of the array dimensions of the
        # image.

        if hdr is not None:
            self.wcs = wcs_from_header(hdr, naxis=2)
            try:
                self.naxis1 = hdr['NAXIS1']
                self.naxis2 = hdr['NAXIS2']
            except:
                if shape is not None:
                    self.naxis1 = shape[1]
                    self.naxis2 = shape[0]
                else:
                    self.naxis1 = 0
                    self.naxis2 = 0
            # bug if naxis=3
            # http://mail.scipy.org/pipermail/astropy/2011-April/001242.html

        # If no FITS header is provided, initialize the WCS object from
        # the other parameters of the constructor.

        else:

            # Define a function that checks that 2D attributes are
            # either a 2-element tuple of float or int, or a float or
            # int scalar which is converted to a 2-element tuple.

            def check_attrs(val, types=(int, float)):
                """Check attribute dimensions."""
                if isinstance(val, types):
                    return (val, val)
                elif len(val) > 2:
                    raise ValueError('dimension > 2')
                else:
                    return val

            crval = check_attrs(crval)
            cdelt = check_attrs(cdelt)

            if crpix is not None:
                crpix = check_attrs(crpix)

            if shape is not None:
                shape = check_attrs(shape, types=int)

            # Create a pywcs object.

            self.wcs = pywcs.WCS(naxis=2)

            # Get the FITS array indexes of the reference pixel.
            # Beware that FITS array indexes are offset by 1 from
            # python array indexes.

            if crpix is not None:
                self.wcs.wcs.crpix = np.array([crpix[1], crpix[0]])
            elif shape is None:
                self.wcs.wcs.crpix = np.array([1.0, 1.0])
            else:
                self.wcs.wcs.crpix = (np.array([shape[1], shape[0]]) + 1) / 2.

            # Get the world coordinate value of reference pixel.

            self.wcs.wcs.crval = np.array([crval[1], crval[0]])
            if deg:  # in decimal degree
                self.wcs.wcs.ctype = ['RA---TAN', 'DEC--TAN']
                self.wcs.wcs.cunit = ['deg', 'deg']
            else:   # in pixel or arcsec
                self.wcs.wcs.ctype = ['LINEAR', 'LINEAR']
                self.wcs.wcs.cunit = ['pixel', 'pixel']

            # If a CD rotation matrix has been provided by the caller,
            # install it.

            if cd is not None and cd.shape[0] == 2 and cd.shape[1] == 2:
                self.wcs.wcs.cd = cd

            # If no CD matrix was provided, construct one from the
            # cdelt and rot parameters, following the official
            # prescription given by equation 189 of Calabretta, M. R.,
            # and Greisen, E. W, Astronomy & Astrophysics, 395,
            # 1077-1122, 2002.

            else:
                rho = np.deg2rad(rot)
                sin_rho = np.sin(rho)
                cos_rho = np.cos(rho)
                self.wcs.wcs.cd = np.array([
                    [cdelt[1] * cos_rho, -cdelt[0] * sin_rho],
                    [cdelt[1] * sin_rho,  cdelt[0] * cos_rho]])

            # Update the wcs object to accomodate the new value of
            # the CD matrix.

            self.wcs.wcs.set()

            # Get the dimensions of the image array.

            if shape is not None:
                self.naxis1 = shape[1]
                self.naxis2 = shape[0]
            else:
                self.naxis1 = 0
                self.naxis2 = 0

    def copy(self):
        """Return a copy of a WCS object."""
        out = WCS()
        out.wcs = self.wcs.deepcopy()
        out.naxis1 = self.naxis1
        out.naxis2 = self.naxis2
        return out

    def info(self):
        """Print information about a WCS object."""
        try:
            dy, dx = self.get_step(unit=u.arcsec)
            sizex = dx * self.naxis1  # ra
            sizey = dy * self.naxis2  # dec
            # center in sexadecimal
            xc = (self.naxis1 - 1) / 2.
            yc = (self.naxis2 - 1) / 2.
            pixsky = self.pix2sky([yc, xc], unit=u.deg)
            sexa = deg2sexa(pixsky)
            ra = sexa[0][1]
            dec = sexa[0][0]
            self._logger.info('center:(%s,%s) size in arcsec:(%0.3f,%0.3f) '
                              'step in arcsec:(%0.3f,%0.3f) rot:%0.1f deg',
                              dec, ra, sizey, sizex, dy, dx, self.get_rot())
        except:
            pixcrd = [[0, 0], [self.naxis2 - 1, self.naxis1 - 1]]
            pixsky = self.pix2sky(pixcrd)
            dy, dx = self.get_step()
            self._logger.info(
                'spatial coord (%s): min:(%0.1f,%0.1f) max:(%0.1f,%0.1f) '
                'step:(%0.1f,%0.1f) rot:%0.1f deg', self.unit,
                pixsky[0, 0], pixsky[0, 1], pixsky[1, 0], pixsky[1, 1],
                dy, dx, self.get_rot())

    def to_header(self):
        """Generate an astropy.fits header object containing the WCS information."""
        has_cd = self.wcs.wcs.has_cd()
        hdr = self.wcs.to_header()
        if has_cd:
            for ci in range(1,3):
                cdelt =  hdr.pop('CDELT%i'%ci, 1)
                for cj in range(1,3):
                    try:
                        val = cdelt * hdr.pop('PC%i_%i'%(ci, cj))
                    except KeyError:
                        if ci==cj:
                            val = cdelt
                        else:
                            val = 0.
                    hdr['CD%i_%i'%(ci, cj)] = val
        return hdr

    def sky2pix(self, x, nearest=False, unit=None):
        """Convert world coordinates (dec,ra) to image pixel indexes (y,x).

        If nearest=True; returns the nearest integer pixel.

        Parameters
        ----------
        x : array
            An (n,2) array of dec- and ra- world coordinates.
        nearest : bool
            If nearest is True returns the nearest integer pixel
            in place of the decimal pixel.
        unit : astropy.units
            The units of the world coordinates

        Returns
        -------
        out : (n,2) array of image pixel indexes. These are
              python array indexes, ordered like (y,x) and with
              0,0 denoting the lower left pixel of the image.

        """
        x = np.asarray(x, dtype=np.float64)
        if x.shape == (2,):
            x = x.reshape(1, 2)
        elif len(x.shape) != 2 or x.shape[1] != 2:
            raise IOError('invalid input coordinates for sky2pix')

        if unit is not None:
            x[:, 1] = (x[:, 1] * unit).to(self.unit).value
            x[:, 0] = (x[:, 0] * unit).to(self.unit).value

        # Tell world2pix to convert the world coordinates to
        # zero-relative array indexes.

        ax, ay = self.wcs.wcs_world2pix(x[:, 1], x[:, 0], 0)
        res = np.array([ay, ax]).T

        if nearest:
            res = (res + 0.5).astype(int)
            if self.naxis1 != 0 and self.naxis2 != 0:
                np.minimum(res, [self.naxis2 - 1, self.naxis1 - 1], out=res)
                np.maximum(res, [0, 0], out=res)
        return res

    def pix2sky(self, x, unit=None):
        """Convert image pixel indexes (y,x) to world coordinates (dec,ra)

        Parameters
        ----------
        x : array
            An (n,2) array of image pixel indexes. These should be
            python array indexes, ordered like (y,x) and with
            0,0 denoting the lower left pixel of the image.
        unit : astropy.units
            The units of the world coordinates.

        Returns
        -------
        out : (n,2) array of dec- and ra- world coordinates.

        """
        x = np.asarray(x, dtype=np.float64)
        if x.shape == (2,):
            x = x.reshape(1, 2)
        elif len(x.shape) != 2 or x.shape[1] != 2:
            raise IOError('invalid input coordinates for pix2sky')

        # Tell world2pix to treat the pixel indexes as zero relative
        # array indexes.

        ra, dec = self.wcs.wcs_pix2world(x[:, 1], x[:, 0], 0)
        if unit is not None:
            ra = (ra * self.unit).to(unit).value
            dec = (dec * self.unit).to(unit).value

        return np.array([dec, ra]).T

    def isEqual(self, other):
        """Return True if other and self have the same attributes.
        Beware that if the two wcs objects have the same world
        coordinate characteristics, but come from images of
        different dimensions, the objects will be considered
        different.

        Parameters
        ----------
        other : WCS
            The wcs object to be compared to self.

        Returns
        -------
        out : boolean
            True if the two WCS objects have the same attributes.

        """

        if not isinstance(other, WCS):
            return False

        cdelt1 = self.get_step()
        cdelt2 = other.get_step(unit=self.unit)
        x1 = self.pix2sky([0, 0])[0]
        x2 = other.pix2sky([0, 0], unit=self.unit)[0]
        return (self.naxis1 == other.naxis1 and
                self.naxis2 == other.naxis2 and
                np.allclose(x1, x2, atol=1E-3, rtol=0) and
                np.allclose(cdelt1, cdelt2, atol=1E-3, rtol=0) and
                np.allclose(self.get_rot(), other.get_rot(), atol=1E-3,
                            rtol=0))

    def sameStep(self, other):
        """Return True if other and self have the same pixel sizes.

        Parameters
        ----------
        other : WCS
            The wcs object to compare to self.

        Returns
        -------
        out : boolean
            True if the two arrays of axis step increments are equal.
        """

        if not isinstance(other, WCS):
            return False

        steps1 = self.get_step()
        steps2 = other.get_step(unit=self.unit)
        return np.allclose(steps1, steps2, atol=1E-7, rtol=0)

    def __getitem__(self, item):
        """Return a WCS object of a 2D slice"""

        # The caller is expected to have specified a 2D slice,
        # so there should be a tuple of two items.

        if isinstance(item, tuple) and len(item) == 2:

            # See if a slice object was sent for the X axis.

            if isinstance(item[1], slice):

                # If a start index was provided, limit it to the extent of
                # the x-axis. If no start index was provided, default to
                # zero.

                if item[1].start is None:
                    imin = 0
                else:
                    imin = int(item[1].start)
                    if imin < 0:
                        imin = self.naxis1 + imin
                    if imin > self.naxis1:
                        imin = self.naxis1

                # If a stop index was provided, limit it to the extent of the
                # X axis. Otherwise substitute the size of the X-axis.

                if item[1].stop is None:
                    imax = self.naxis1
                else:
                    imax = int(item[1].stop)
                    if imax < 0:
                        imax = self.naxis1 + imax
                    if imax > self.naxis1:
                        imax = self.naxis1

                # If a step was provided and it isn't 1, complain
                # because we can't accomodate gaps between pixels.

                if item[1].step is not None and item[1].step != 1:
                    raise ValueError('Index steps are not supported')

            # If a slice object wasn't sent, then maybe a single index
            # was passed for the X axis. If so, select the specified
            # single pixel.

            else:
                imin = int(item[1])
                imax = int(item[1] + 1)

            # See if a slice object was sent for the Y axis.

            if isinstance(item[0], slice):

                # If a start index was provided, limit it to the extent of
                # the y-axis. If no start index was provided, default to
                # zero.

                if item[0].start is None:
                    jmin = 0
                else:
                    jmin = int(item[0].start)
                    if jmin < 0:
                        jmin = self.naxis2 + jmin
                    if jmin > self.naxis2:
                        jmin = self.naxis2

                # If a stop index was provided, limit it to the extent of the
                # Y axis. Otherwise substitute the size of the Y-axis.

                if item[0].stop is None:
                    jmax = self.naxis2
                else:
                    jmax = int(item[0].stop)
                    if jmax < 0:
                        jmax = self.naxis2 + jmax
                        if jmax > self.naxis2:
                            jmax = self.naxis2

                # If an index step was provided and it isn't 1, reject
                # the call, because we can't accomodate gaps between selected
                # pixels.

                if item[1].step is not None and item[1].step != 1:
                    raise ValueError('Index steps are not supported')

            # If a slice object wasn't sent, then maybe a single index
            # was passed for the Y axis. If so, select the specified
            # single pixel.

            else:
                jmin = int(item[0])
                jmax = int(item[0] + 1)

            # Compute the array indexes of the coordinate reference
            # pixel in the sliced array. Note that this can indicate a
            # pixel outside the slice.

            crpix = (self.wcs.wcs.crpix[0] - imin,
                     self.wcs.wcs.crpix[1] - jmin)

            # Get a copy of the original WCS object.

            res = self.copy()

            # Record the new coordinate reference pixel index and the
            # reduced dimensions of the selected sub-image.

            res.wcs.wcs.crpix = np.array(crpix)
            res.naxis1 = int(imax - imin)
            res.naxis2 = int(jmax - jmin)

            # Recompute the characteristics of the new WCS object.

            res.wcs.wcs.set()

            # Return the sliced WCS object.

            return res
        else:
            raise ValueError('Missing 2D slice indexes')

    def get_step(self, unit=None):
        """Return [dDec,dRa].

        Parameters
        ----------
        unit : astropy.units
            type of the world coordinates

        """
        try:
            dy, dx = np.sqrt(np.sum(self.wcs.wcs.cd ** 2, axis=1))[::-1]
        except:
            try:
                cdelt = self.wcs.wcs.get_cdelt()
                pc = self.wcs.wcs.get_pc()
                dx = cdelt[0] * np.sqrt(pc[0, 0] ** 2 + pc[0, 1] ** 2)
                dy = cdelt[1] * np.sqrt(pc[1, 0] ** 2 + pc[1, 1] ** 2)
            except:
                raise IOError('No standard WCS')

        if unit:
            dx = (dx * self.unit).to(unit).value
            dy = (dy * self.unit).to(unit).value
        return np.array([dy, dx])

    def get_range(self, unit=None):
        """Return [ [dec_min,ra_min], [dec_max,ra_max] ]

        Parameters
        ----------
        unit : astropy.units
            type of the world coordinates

        """
        pixcrd = [[0, 0], [self.naxis2 - 1, 0], [0, self.naxis1 - 1],
                  [self.naxis2 - 1, self.naxis1 - 1]]
        pixsky = self.pix2sky(pixcrd, unit=unit)
        return np.vstack([pixsky.min(axis=0), pixsky.max(axis=0)])

    def get_start(self, unit=None):
        """Return the [dec,ra] coordinates of pixel (0,0).

        Parameters
        ----------
        unit : astropy.units
            The angular units of the returned coordinates.

        Returns
        -------
        out : numpy.ndarray
           The equatorial coordinate of pixel [0,0], ordered as:
           [dec,ra]. If a value was given to the optional 'unit'
           argument, the angular unit specified there will be used for
           the return value. Otherwise the unit stored in the
           self.unit property will be used.

        """
        pixcrd = [[0, 0]]
        pixsky = self.pix2sky(pixcrd, unit=unit)
        return np.array([pixsky[0, 0], pixsky[0, 1]])

    def get_end(self, unit=None):
        """Return the [dec,ra] coordinates of pixel (-1,-1).

        Parameters
        ----------
        unit : astropy.units
            The angular units of the returned coordinates.

        Returns
        -------
        out : numpy.ndarray
           The equatorial coordinate of pixel [-1,-1], ordered as,
           [dec,ra]. If a value was given to the optional 'unit'
           argument, the angular unit specified there will be used for
           the return value. Otherwise the unit stored in the
           self.unit property will be used.

        """
        pixcrd = [[self.naxis2 - 1, self.naxis1 - 1]]
        pixsky = self.pix2sky(pixcrd, unit=unit)
        return np.array([pixsky[0, 0], pixsky[0, 1]])

    def get_rot(self, unit=u.deg):
        """Return the rotation angle of the image relative to the sky.

        Parameters
        ----------
        unit : astropy.units
            type of the angle coordinate, degree by default

        """
        try:
            theta = np.arctan2(self.wcs.wcs.cd[1, 0], self.wcs.wcs.cd[1, 1])
        except:
            try:
                pc = self.wcs.wcs.get_pc()
                theta = np.arctan2(pc[1, 0], pc[1, 1])
                # return np.rad2deg(np.arctan2(self.wcs.wcs.pc[1, 0], \
                #                          self.wcs.wcs.pc[1, 1]))
            except:
                raise IOError('No standard WCS')
        return (theta * u.rad).to(unit).value

    def get_cd(self):
        """Return the CD matrix."""
        try:
            return self.wcs.wcs.cd
        except:
            try:
                # cd = self.wcs.wcs.pc
                # cd[0,:] *= self.wcs.wcs.cdelt[0]
                # cd[1,:] *= self.wcs.wcs.cdelt[1]
                cdelt = self.wcs.wcs.get_cdelt()
                cd = self.wcs.wcs.get_pc().__copy__()
                cd[0, :] *= cdelt[0]
                cd[1, :] *= cdelt[1]
                return cd
            except:
                raise IOError('No standard WCS')

    def get_naxis1(self):
        """Return the value of the FITS NAXIS1 parameter.

        NAXIS1 holds the dimension of the X-axis of the image. In the
        data-array of an MPDAF Image object, this is the dimension of
        axis 1 of the python array that contains the image. If im is
        an mpdaf.obj.Image object, then im.shape[1] is equivalent to
        im.wcs.get_naxis1().

        Returns
        -------
        out : int
           The value of the FITS NAXIS1 parameter.

        """
        return self.naxis1

    def get_naxis2(self):
        """Return the value of the FITS NAXIS2 parameter.

        NAXIS2 holds the dimension of the Y-axis of the image. In the
        data-array of an MPDAF Image object, this is the dimension of
        axis 0 of the python array that contains the image. If im is
        an mpdaf.obj.Image object, then im.shape[0] is equivalent to
        im.wcs.get_naxis2().

        Returns
        -------
        out : int
           The value of the FITS NAXIS2 parameter.

        """
        return self.naxis2

    def get_crpix1(self):
        """Return the value of the FITS CRPIX1 parameter.

        CRPIX1 contains the index of the reference position of
        the image along the X-axis of the image. Beware that
        this is a FITS array index, which is 1 greater than the
        corresponding python array index. For example, a crpix
        value of 1 denotes a python array index of 0. The
        reference pixel index is a floating point value that
        can indicate a position between two pixels. It can also
        indicate an index that is outside the bounds of the
        array.

        Returns
        -------
        out : float
           The value of the FITS CRPIX1 parameter.

        """
        return self.wcs.wcs.crpix[0]

    def get_crpix2(self):
        """Return the value of the FITS CRPIX2 parameter.

        CRPIX2 contains the index of the reference position of
        the image along the Y-axis of the image. Beware that
        this is a FITS array index, which is 1 greater than the
        corresponding python array index. For example, a crpix
        value of 1 denotes a python array index of 0. The
        reference pixel index is a floating point value that
        can indicate a position between two pixels. It can also
        indicate an index that is outside the bounds of the
        array.

        Returns
        -------
        out : float
           The value of the FITS CRPIX2 parameter.

        """
        return self.wcs.wcs.crpix[1]

    def get_crval1(self, unit=None):
        """Return the value of the FITS CRVAL1 parameter.

        CRVAL1 contains the coordinate reference value of the first
        image axis (eg. right-ascension).

        Parameters
        ----------
        unit : astropy.units
            The angular units to give the return value.

        Returns
        -------
        out : float
           The value of CRVAL1 in the specified angular units. If the
           units are not given, then the unit in the self.unit
           property is used.

        """
        if unit is None:
            return self.wcs.wcs.crval[0]
        else:
            return (self.wcs.wcs.crval[0] * self.unit).to(unit).value

    def get_crval2(self, unit=None):
        """Return the value of the FITS CRVAL2 parameter.

        CRVAL2 contains the coordinate reference value of the second
        image axis (eg. declination).

        Parameters
        ----------
        unit : astropy.units
            The angular units to give the return value.

        Returns
        -------
        out : float
           The value of CRVAL2 in the specified angular units. If the
           units are not given, then the unit in the self.unit
           property is used.

        """
        if unit is None:
            return self.wcs.wcs.crval[1]
        else:
            return (self.wcs.wcs.crval[1] * self.unit).to(unit).value

    @property
    def unit(self):
        """Return the default angular unit used for sky coordinates.

        Returns
        -------
        out : astropy.units
           The unit to use for coordinate angles.

        """

        if self.wcs.wcs.cunit[0] != self.wcs.wcs.cunit[1]:
            self._logger.warning('different units on x- and y-axes')
        return self.wcs.wcs.cunit[0]

    def set_naxis1(self, n):
        """NAXIS1 setter (first dimension of an image)."""
        self.naxis1 = n

    def set_naxis2(self, n):
        """NAXIS2 setter (second dimension of an image)."""
        self.naxis2 = n

    def set_crpix1(self, x):
        """CRPIX1 setter (reference pixel on the first axis)."""
        self.wcs.wcs.crpix[0] = x
        self.wcs.wcs.set()

    def set_crpix2(self, y):
        """Set the value of the FITS CRPIX1 parameter, which sets the
        reference pixel index along the Y-axis of the image.

        This is a floating point value which can denote a position
        between pixels. It is specified with the FITS indexing
        convention, where FITS pixel 1 is equivalent to pixel 0 in
        python arrays. In general subtract 1 from y to get the
        corresponding floating-point pixel index along axis 0 of the
        image array.  In cases where y is an integer, the
        corresponding column in the python data array that contains
        the image is data[y-1,:].

        Parameters
        ----------
        y : float
            The index of the reference pixel along the Y axis.
        """

        self.wcs.wcs.crpix[1] = y
        self.wcs.wcs.set()

    def set_crval1(self, x, unit=None):

        """Set the value of the CRVAL1 keyword, which indicates the coordinate
        reference value along the first image axis (eg. right
        ascension).

        Parameters
        ----------
        x : float
            The value of the reference pixel on the first axis.
        unit : astropy.units
            The angular units of the world coordinates.

        """
        if unit is None:
            self.wcs.wcs.crval[0] = x
        else:
            self.wcs.wcs.crval[0] = (x * unit).to(self.unit).value
        self.wcs.wcs.set()

    def set_crval2(self, x, unit=None):
        """CRVAL2 setter (value of the reference pixel on the second axis).

        Parameters
        ----------
        x : float
            The value of the reference pixel on the second axis.
        unit : astropy.units
            The angular units of the world coordinates.
        """
        if unit is None:
            self.wcs.wcs.crval[1] = x
        else:
            self.wcs.wcs.crval[1] = (x * unit).to(self.unit).value
        self.wcs.wcs.set()

    def set_step(self, step, unit=None):
        """Update the step in the CD matrix or in the PC matrix."""
        if unit is not None:
            step[0] = (step[0] * unit).to(self.unit).value
            step[1] = (step[1] * unit).to(self.unit).value

        theta = self.get_rot()
        if np.abs(theta) > 1E-3:
            self.rotate(-theta)
        if self.is_deg():  # in decimal degree
            self.wcs.wcs.cd = np.array([[-step[1], 0], [0, step[0]]])
        else:   # in pixel or arcsec
            self.wcs.wcs.cd = np.array([[step[1], 0], [0, step[0]]])
        self.wcs.wcs.set()
        if np.abs(theta) > 1E-3:
            self.rotate(theta)

    def rotate(self, theta):
        """Rotate WCS coordinates to new orientation given by theta.

        Parameters
        ----------
        theta : float
            Rotation in degree.
        """
        # rotation matrix of -theta
        _theta = np.deg2rad(theta)
        _mrot = np.zeros(shape=(2, 2), dtype=np.double)
        _mrot[0] = (np.cos(_theta), -np.sin(_theta))
        _mrot[1] = (np.sin(_theta), np.cos(_theta))
        try:
            new_cd = np.dot(self.wcs.wcs.cd, _mrot)
            self.wcs.wcs.cd = new_cd
            self.wcs.wcs.set()
        except:
            try:
                # new_pc = np.dot(self.wcs.wcs.pc, _mrot)
                new_pc = np.dot(self.wcs.wcs.get_pc(), _mrot)
                self.wcs.wcs.pc = new_pc
                self.wcs.wcs.set()
            except:
                raise StandardError("problem with wcs rotation")

    def resample(self, step, start, unit=None):
        """Resample to a new coordinate system.

        Parameters
        ----------
        start : float or (float, float)
            New positions (dec,ra) for the pixel (0,0).
            If None, old position is used.
        step : float or (float, float)
            New step (ddec,dra).
        unit : astropy.units
            type of the world coordinates for the start and step parameters.

        Returns
        -------
        out : WCS

        """
        if unit is not None:
            step[0] = (step[0] * unit).to(self.unit).value
            step[1] = (step[1] * unit).to(self.unit).value
            if start is not None:
                start[0] = (start[0] * unit).to(self.unit).value
                start[1] = (start[1] * unit).to(self.unit).value

        cdelt = self.get_step()
        if start is None:
            xc = 0
            yc = 0
            pixsky = self.pix2sky([xc, yc])
            start = (pixsky[0][0] - 0.5 * cdelt[0] + 0.5 * step[0],
                     pixsky[0][1] - 0.5 * cdelt[1] + 0.5 * step[1])

        old_start = self.get_start()
        res = self.copy()
        res.set_crpix1(1.0)
        res.set_crpix2(1.0)
        res.set_crval1(start[1], unit=None)
        res.set_crval2(start[0], unit=None)
        res.set_step(step, unit=None)
        res.naxis1 = int(np.ceil((self.naxis1 * cdelt[1] - start[1] +
                                  old_start[1]) / step[1]))
        res.naxis2 = int(np.ceil((self.naxis2 * cdelt[0] - start[0] +
                                  old_start[0]) / step[0]))
        return res

    def rebin(self, factor):
        """Rebin to a new coordinate system.

        This is a helper function for the Image.rebin_mean() and
        Image.rebin_median() functions.

        Parameters
        ----------
        factor : (integer,integer)
            Factor in y and x.

        Returns
        -------
        out : WCS
        """
        res = self.copy()
        factor = np.array(factor)

        try:
            cd = res.wcs.wcs.cd
            cd[0, :] *= factor[1]
            cd[1, :] *= factor[0]
            res.wcs.wcs.cd = cd
        except:
            try:
                cdelt = res.wcs.wcs.cdelt
                cdelt[0] *= factor[1]
                cdelt[1] *= factor[0]
                res.wcs.wcs.cdelt = cdelt
            except:
                raise StandardError("problem in wcs rebinning")
        res.wcs.wcs.set()
        old_cdelt = self.get_step()
        cdelt = res.get_step()

        crpix = res.wcs.wcs.crpix
        crpix[0] = (crpix[0] * old_cdelt[1] - old_cdelt[1] / 2.0 +
                    cdelt[1] / 2.0) / cdelt[1]
        crpix[1] = (crpix[1] * old_cdelt[0] - old_cdelt[0] / 2.0 +
                    cdelt[0] / 2.0) / cdelt[0]
        res.wcs.wcs.crpix = crpix
        res.naxis1 = res.naxis1 / factor[1]
        res.naxis2 = res.naxis2 / factor[0]
        res.wcs.wcs.set()

        return res

    def is_deg(self):
        """Return True if world coordinates are in decimal degrees
        (CTYPE1='RA---TAN',CTYPE2='DEC--TAN',CUNIT1=CUNIT2='deg).
        """
        try:
            return self.wcs.wcs.ctype[0] not in ('LINEAR', 'PIXEL')
        except:
            return True

    def to_cube_header(self, wave):
        """Generate an astropy.fits header object with WCS information and
        wavelength information."""
        hdr = self.to_header()
        if wave is not None:
            hdr.update(wave.to_header(naxis=3, use_cd='CD1_1' in hdr))
        return hdr


class WaveCoord(object):

    """WaveCoord class manages world coordinates in spectral direction.

    Parameters
    ----------
    hdr : astropy.fits.CardList
        A FITS header. If hdr is not None, WaveCoord object is created from
        this header and other parameters are not used.
    crpix : float
        Reference pixel coordinates. 1.0 by default. Note that for crpix
        definition, the first pixel in the spectrum has pixel coordinates.
    cdelt : float
        Step in wavelength (1.0 by default).
    crval : float
        Coordinates of the reference pixel (0.0 by default).
    cunit : u.unit
        Wavelength unit (Angstrom by default).
    ctype : string
        Type of the coordinates.
    shape : integer or None
        Size of spectrum (no mandatory).

    Attributes
    ----------
    shape : integer
        Size of spectrum.
    wcs : astropy.wcs.WCS
        Wavelength coordinates.

    """

    def __init__(self, hdr=None, crpix=1.0, cdelt=1.0, crval=1.0,
                 cunit=u.angstrom, ctype='LINEAR', shape=None):
        self._logger = logging.getLogger(__name__)
        self.shape = shape
        self.unit = cunit

        if hdr is not None:
            hdr = hdr.copy()
            try:
                n = hdr['NAXIS']
                self.shape = hdr['NAXIS%d' % n]
            except:
                n = hdr['WCSAXES']

            axis = 1 if n == 1 else 3
            # Get the unit and remove it from the header so that wcslib does
            # not convert the values.
            self.unit = u.Unit(fix_unit_read(hdr.pop('CUNIT%d' % axis)))
            self.wcs = wcs_from_header(hdr).sub([axis])
            if shape is not None:
                self.shape = shape
        else:
            self.unit = u.Unit(cunit)
            self.wcs = pywcs.WCS(naxis=1)
            self.wcs.wcs.crpix[0] = crpix
            self.wcs.wcs.cdelt[0] = cdelt
            self.wcs.wcs.ctype[0] = ctype
            self.wcs.wcs.crval[0] = crval
            self.wcs.wcs.set()

    def copy(self):
        """Copie WaveCoord object in a new one and returns it."""
        # remove the  UnitsWarning: The unit 'Angstrom' has been deprecated in
        # the FITS standard.
        out = WaveCoord(shape=self.shape, cunit=self.unit)
        out.wcs = self.wcs.deepcopy()
        return out

    def info(self, unit=None):
        """Print information."""
        unit = unit or self.unit
        start = self.get_start(unit=unit)
        step = self.get_step(unit=unit)

        if self.shape is None:
            self._logger.info('wavelength: min:%0.2f step:%0.2f %s',
                              start, step, unit)
        else:
            end = self.get_end(unit=unit)
            self._logger.info('wavelength: min:%0.2f max:%0.2f step:%0.2f %s',
                              start, end, step, unit)

    def isEqual(self, other):
        """Return True if other and self have the same attributes."""
        if not isinstance(other, WaveCoord):
            return False

        l1 = self.coord(0, unit=self.unit)
        l2 = other.coord(0, unit=self.unit)
        return (self.shape == other.shape and
                np.allclose(l1, l2, atol=1E-2, rtol=0) and
                np.allclose(self.get_step(), other.get_step(unit=self.unit),
                            atol=1E-2, rtol=0) and
                self.wcs.wcs.ctype[0] == other.wcs.wcs.ctype[0])

    def coord(self, pixel=None, unit=None):
        """Return the coordinate corresponding to pixel. If pixel is None
        (default value), the full coordinate array is returned.

        Parameters
        ----------
        pixel : integer, array or None.
            pixel value.
        unit : astropy.units
            type of the wavelength coordinates

        Returns
        -------
        out : float or array of float

        """
        if pixel is None and self.shape is None:
            raise IOError("wavelength coordinates without dimension")

        if pixel is None:
            pixelarr = np.arange(self.shape, dtype=float)
        elif is_float(pixel) or is_int(pixel):
            pixelarr = np.ones(1) * pixel
        else:
            pixelarr = np.asarray(pixel)
        res = self.wcs.wcs_pix2world(pixelarr, 0)[0]
        if unit is not None:
            res = (res * self.unit).to(unit).value
        return res[0] if isinstance(pixel, (int, float)) else res

    def pixel(self, lbda, nearest=False, unit=None):
        """Return the decimal pixel corresponding to the wavelength lbda.

        If nearest=True; returns the nearest integer pixel.

        Parameters
        ----------
        lbda : float or array
            wavelength value.
        nearest : bool
            If nearest is True returns the nearest integer pixel
            in place of the decimal pixel.
        unit : astropy.units
            type of the wavelength coordinates

        Returns
        -------
        out : float or integer

        """

        lbdarr = np.asarray([lbda] if isinstance(lbda, (int, float)) else lbda)
        if unit is not None:
            lbdarr = (lbdarr * unit).to(self.unit).value
        pix = self.wcs.wcs_world2pix(lbdarr, 0)[0]
        if nearest:
            pix = (pix + 0.5).astype(int)
            np.maximum(pix, 0, out=pix)
            if self.shape is not None:
                np.minimum(pix, self.shape - 1, out=pix)
        return pix[0] if isinstance(lbda, (int, float)) else pix

    def __getitem__(self, item):
        """Return the coordinate corresponding to pixel if item is an integer
        Return the corresponding WaveCoord object if item is a slice."""

        if item is None:
            return self
        elif isinstance(item, int):
            if item >= 0:
                lbda = self.coord(pixel=item)
            else:
                if self.shape is None:
                    raise ValueError('wavelength coordinates without dimension')
                else:
                    lbda = self.coord(pixel=self.shape + item)
            return WaveCoord(crpix=1.0, cdelt=0, crval=lbda,
                             cunit=self.unit, shape=1,
                             ctype=self.wcs.wcs.ctype[0])
        elif isinstance(item, slice):
            if item.start is None:
                start = 0
            elif item.start >= 0:
                start = item.start
            else:
                if self.shape is None:
                    raise ValueError('wavelength coordinates without dimension')
                else:
                    start = self.shape + item.start
            if item.stop is None:
                if self.shape is None:
                    raise ValueError('wavelength coordinates without dimension')
                else:
                    stop = self.shape
            elif item.stop >= 0:
                stop = item.stop
            else:
                if self.shape is None:
                    raise ValueError('wavelength coordinates without dimension')
                else:
                    stop = self.shape + item.stop
            newlbda = self.coord(pixel=np.arange(start, stop, item.step))
            dim = newlbda.shape[0]
            if dim < 2:
                raise ValueError('Spectrum with dim < 2')
            cdelt = newlbda[1] - newlbda[0]
            return WaveCoord(crpix=1.0, cdelt=cdelt, crval=newlbda[0],
                             cunit=self.unit, shape=dim,
                             ctype=self.wcs.wcs.ctype[0])
        else:
            raise ValueError('Operation forbidden')

    def resample(self, step, start, unit=None):
        """Resample to a new coordinate system.

        Parameters
        ----------
        start : float
            New wavelength for the pixel 0.
        step : float
            New step.
        unit : astropy.units
            type of the wavelength coordinates

        Returns
        -------
        out : WaveCoord

        """
        if unit is not None:
            step = (step * unit).to(self.unit).value
            if start is not None:
                start = (start * unit).to(self.unit).value

        cdelt = self.get_step()
        if start is None:
            pix0 = self.coord(0)
            start = pix0 - 0.5 * cdelt + 0.5 * step

        old_start = self.get_start()
        res = self.copy()
        res.wcs.wcs.crpix[0] = 1.0
        res.wcs.wcs.crval[0] = start
        try:
            res.wcs.wcs.cd[0][0] = step
        except:
            try:
                res.wcs.wcs.cdelt[0] = 1.0
                res.wcs.wcs.pc[0][0] = step
            except:
                raise IOError('No standard WCS')
        res.wcs.wcs.set()
        res.shape = int(np.ceil((self.shape * cdelt - start + old_start) /
                                step))
        return res

    def rebin(self, factor):
        """Rebin to a new coordinate system (in place).

        Parameters
        ----------
        factor : integer
            Factor.

        Returns
        -------
        out : WaveCoord

        """
        old_cdelt = self.get_step()

        try:
            self.wcs.wcs.cd = self.wcs.wcs.cd * factor
        except:
            try:
                self.wcs.wcs.cdelt = self.wcs.wcs.cdelt * factor
            except:
                raise StandardError("problem in wcs rebinning")
        self.wcs.wcs.set()
        cdelt = self.get_step()

        crpix = self.wcs.wcs.crpix[0]
        crpix = (crpix * old_cdelt - old_cdelt / 2.0 + cdelt / 2.0) / cdelt
        self.wcs.wcs.crpix[0] = crpix
        self.shape = self.shape / factor
        self.wcs.wcs.set()

    def get_step(self, unit=None):
        """Return the step in wavelength.

        Parameters
        ----------
        unit : astropy.units
            type of the wavelength coordinates

        """
        if self.wcs.wcs.has_cd():
            step = self.wcs.wcs.cd[0][0]
        else:
            cdelt = self.wcs.wcs.get_cdelt()[0]
            pc = self.wcs.wcs.get_pc()[0, 0]
            step = (cdelt * pc)

        if unit is not None:
            step = (step * self.unit).to(unit).value
        return step
    
    def set_step(self, x, unit=None):
        """Return the step in wavelength.

        Parameters
        ----------
        x : float
            Step value
        unit : astropy.units
            type of the wavelength coordinates
        """
        if unit is not None:
            step = (x * unit).to(self.unit).value
        else:
            step = x
        
        if self.wcs.wcs.has_cd():
            self.wcs.wcs.cd[0][0] = step
        else:
            pc = self.wcs.wcs.get_pc()[0, 0]
            self.wcs.wcs.cdelt[0] = step / pc
        self.wcs.wcs.set()

    def get_start(self, unit=None):
        """Return the value of the first pixel.

        Parameters
        ----------
        unit : astropy.units
            type of the wavelength coordinates

        """
        return self.coord(0, unit)

    def get_end(self, unit=None):
        """Return the value of the last pixel.

        Parameters
        ----------
        unit : astropy.units
            type of the wavelength coordinates

        """
        if self.shape is None:
            raise IOError("wavelength coordinates without dimension")
        else:
            return self.coord(self.shape - 1, unit)

    def get_range(self, unit=None):
        """Return the wavelength range [Lambda_min,Lambda_max].

        Parameters
        ----------
        unit : astropy.units
            type of the wavelength coordinates

        """
        if self.shape is None:
            raise IOError("wavelength coordinates without dimension")
        else:
            return self.coord([0, self.shape - 1], unit)

    def get_crpix(self):
        """CRPIX getter (reference pixel on the wavelength axis)."""
        return self.wcs.wcs.crpix[0]

    def set_crpix(self, x):
        """CRPIX setter (reference pixel on the wavelength axis)."""
        self.wcs.wcs.crpix[0] = x
        self.wcs.wcs.set()

    def get_crval(self, unit=None):
        """CRVAL getter (value of the reference pixel on the wavelength axis).

        Parameters
        ----------
        unit : astropy.units
            type of the wavelength coordinates

        """
        if unit is None:
            return self.wcs.wcs.crval[0]
        else:
            return (self.wcs.wcs.crval[0] * self.unit).to(unit).value
        
    def set_crval(self, x, unit=None):
        """CRVAL getter (value of the reference pixel on the wavelength axis).

        Parameters
        ----------
        x : float
            value of the reference pixel on the wavelength axis
        unit : astropy.units
            type of the wavelength coordinates
        """
        if unit is None:
            self.wcs.wcs.crval[0] = x
        else:
            self.wcs.wcs.crval[0] = (x * unit).to(self.unit).value
        self.wcs.wcs.set()

    def get_ctype(self):
        """Return the type of wavelength coordinates."""
        return self.wcs.wcs.ctype[0]

    def to_header(self, naxis=1, use_cd=False):
        """Generate a astropy.fits header object with the WCS information."""
        hdr = fits.Header()
        hdr['WCSAXES'] = (naxis, 'Number of coordinate axes')
        hdr['CRVAL%d' % naxis] = (self.get_crval(),
                                  'Coordinate value at reference point')
        hdr['CRPIX%d' % naxis] = (self.get_crpix(),
                                  'Pixel coordinate of reference point')
        hdr['CUNIT%d' % naxis] = (self.unit.to_string('fits'),
                                  'Units of coordinate increment and value')
        hdr['CTYPE%d' % naxis] = (self.get_ctype(),
                                  'Coordinate type code')

        if use_cd and naxis == 3:
            hdr['CD3_3'] = self.get_step()
            hdr['CD1_3'] = 0.
            hdr['CD2_3'] = 0.
            hdr['CD3_1'] = 0.
            hdr['CD3_2'] = 0.
        else:
            hdr['CDELT%d' % naxis] = (self.get_step(),
                                      'Coordinate increment at reference '
                                      'point')

        return hdr
