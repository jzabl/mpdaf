"""focus.py contains FOCUS: Fast Object CUbe Search

This software has been developped by Carole Clastres under the supervision of
David Mary (Lagrange institute, University of Nice) and ported to python by
Laure Piqueras (CRAL).

The project is funded by the ERC MUSICOS (Roland Bacon, CRAL). Please contact
Carole for more info at carole.clastres@univ-lyon1.fr
"""

import numpy as np
import logging
from scipy.stats import t
from scipy import ndimage
import os.path

from ..obj import Cube, Image
from ..sdetect import SourceCatalog


class FOCUS(object):

    """This class contains sources detection methods on cube object

    Parameters
    ----------
    cube   : string
             Cube FITS file name.
    expmap : string
             Exposures map FITS file name.

    Attributes
    ----------
    cube   : :class:`mpdaf.obj.Cube`
             Cube object.
    expmap : string
             Exposures map FITS file name.
    """

    def __init__(self, cube, expmap):
        """Creates a SourceDetect3D object.

        Parameters
        ----------
        cube   : string
                 Cube FITS file name.
        expmap : string
                 Exposures map FITS file name.
        """
        self.logger = logging.getLogger('mpdaf corelib')
        self.cube = Cube(cube)
        self.expmap = expmap

    def p_values(self):
        """ computes the false detection probability cube.
        The Student cumulative distribution function
        with expmap-1 degrees of freedom is used. 
 
        Algorithm from Carole Clastre (carole.clastres@univ-lyon1.fr)
 
        Returns
        -------
        out : :class:`mpdaf.obj.Cube`
              Cube containing p_values
        """
        d = {'class': 'SourceDetect3D', 'method': 'p_values'}
        # Load cube
        cube = self.cube.data.data
 
        # Load exposures
        exposures = Cube(self.expmap).data.data
 
        # Weighted cube
        self.logger.info('Compute weighted cube', extra=d)
        if self.cube.var is not None:
            cube_w = cube / np.sqrt(self.cube.var)
        else:
            cube_w = cube.__copy__()
        cube_w = np.nan_to_num(cube_w)
 
        # Compute the p-values with student cumulative distribution function with exposures-1 degrees of freedom
        msg = 'Computing the p-values using student cumulative distribution function with expmap-1 degrees of freedom'
        self.logger.info(msg, extra=d)
        self.logger.info('Please note that it takes some time ...', extra=d)
 
        ksel = np.where(exposures < 2)  # seg fault if not ...
        exposures[ksel] = 2
        cube_w[ksel] = 0
        pval_t = 1.0 - t.cdf(cube_w, exposures - 1, loc=0, scale=1)
        # bug scipy
        Nlambda = self.cube.shape[0]
        for i in range(2000, Nlambda, 2000):
            j = min(Nlambda, 2000 + i)
            pval_t[i:j, :, :] = 1 - t.cdf(cube_w[i:j, :, :], exposures[i:j, :, :] - 1, loc=0, scale=1)
        return Cube(wcs=self.cube.wcs, wave=self.cube.wave, data=pval_t)
 
    def quick_detection(self, p_values, p0=1e-8):
        """ detects quickly bright voxels and builds a catalog of objects.
 
        Algorithm from Carole Clastre (carole.clastres@univ-lyon1.fr)
 
        Parameters
        ----------
        p_values : :class:`mpdaf.obj.Cube`
                   Cube object containing the corresponding p_values
        p0       : float
                   threshold in the p-value domain
 
        Returns
        -------
        imaobj :  :class:`mpdaf.obj.Image`
                  Image containing maximum lambda value of the detected objects
        catalog : :class:`mpdaf.obj.SourceCatalog`
                  Catalog listing the center of mass of the detected components
                  and the maximum wavelengths
        """
        d = {'class': 'SourceDetect3D', 'method': 'quick_detection'}
        # Load cube
        cube = self.cube.data.data
 
        # Weighted cube
        self.logger.info('Computing weighted cube', extra=d)
        if self.cube.var is not None:
            cube_w = cube / np.sqrt(self.cube.var)
        else:
            cube_w = cube.__copy__()
        cube_w = np.nan_to_num(cube_w)
 
        # Dimensions
        # row
        Nx = self.cube.shape[2]
        # column
        Ny = self.cube.shape[1]
 
        # Filter to remove deviant pixels
        self.logger.info('Filtering to remove deviant pixels', extra=d)
        cartemin = np.amin(cube_w, axis=0)
        cartemax = np.amax(cube_w, axis=0)
 
        # p_values
        pval_t = p_values.data.data
 
        self.logger.info('Detecting where p-values<%g' % p0, extra=d)
        # Find the minimum of the p-values
        pval_inf_t = np.amin(pval_t, axis=0)
        lambda_cube = np.argmax(cube_w, axis=0)
 
        # Detection test
        # Test : Detect if p-values<p0
        wavelength = self.cube.wave.coord(lambda_cube)
        filtre = np.where((cartemin > -8) & (cartemax < 80) & (pval_inf_t < p0))
        detect = np.zeros((Ny, Nx))
        detect[filtre] = wavelength[filtre]
 
        self.logger.info('Finding the 8 connected components', extra=d)
        # Count the objects detected
        # Find the 8 connected components in binary image
        structure = ndimage.morphology.generate_binary_structure(2, 8)
        label = ndimage.measurements.label(detect, structure)
        Nobjects = label[1]
 
        pos = ndimage.measurements.center_of_mass(detect, label[0], np.arange(Nobjects) + 1)
 
        # Count the contiguous pixels (at least 2)
        n = 0
        Obj = np.zeros((Nx, Ny))
        catalog = dict()
        for i in range(1, Nobjects):
            ksel = np.where(label[0] == i)
            if (len(ksel[0]) > 1):
                n += 1
                Obj[ksel] = detect[ksel]
                coord = self.cube.wcs.pix2sky(pos[i - 1])[0]
                catalog[tuple(coord)] = np.unique(detect[ksel])
        self.logger.info('%d objects detected' % n, extra=d)
 
        # resulted image
        imaobj = Image(wcs=self.cube.wcs, data=Obj)
        ksel = np.where(Obj == 0)
        imaobj.mask_selection(ksel)
        #imaobj.plot(vmin=4900, vmax=9300, colorbar='v')
 
        # catalog
        try:
            wcs = self.cube.data_header['CUNIT1']
            wave = self.cube.data_header['CUNIT3']
        except:
            wcs = ''
            wave = ''
 
        if p_values.filename is None:
            pval_file = ''
        else:
            pval_file = os.path.basename(p_values.filename)
 
        cat = SourceCatalog(catalog, wcs, wave,
                            "obj.SourceDetect3D.quick_detection",
                            ['cube', 'expmap', 'pvalues', 'p0'],
                            [os.path.basename(self.cube.filename),
                             os.path.basename(self.expmap),
                             pval_file, p0],
                            ['cube', 'expmpa', 'pvalues', 'p0'])
 
        return imaobj, cat