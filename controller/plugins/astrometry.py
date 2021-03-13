from core.plugin import Plugin

from core.utils import Print
import core.constants as cst

from astropy.io import fits
from astropy.stats import sigma_clipped_stats
from photutils import DAOStarFinder
import os
import logging

from astrometry_net_client import Client

class Astrometry(Plugin):
    """ Pipeline plugin that handles the uploading process to astrometry
        and the aftermath.
        
        Huge thanks to Sten Sipma for the astrometry-net-client module!
    """
    def __init__(self):
        super().__init__()
        self.title = "The Astrometry Handler"
        self.description = """ Plugin that runs an Observations light files
                               through Astrometry.
                           """
        
        self.rerun_on_pending = True
        self.rerun_on_astrometry = False

    def on_run(self, obs, working_dir, args):
        FMT = (
            "[%(asctime)s] %(threadName)-8s %(levelname)-8s |"
            " %(funcName)s - %(message)s"
        )
        #logging.basicConfig(level=logging.DEBUG, format=FMT)
        #log = logging.getLogger(__name__)

        api_key = "spkngclyydujeuke"
        
        Print("Initializing client (loggin in)", args)
        c = Client(api_key=api_key)
        Print("Log in done", args)
    
        #files = self.get_reduced_lights(working_dir)[:3]
        files = ["/net/dataserver3/data/users/sterrenwacht/obslog/200418/STL-6303E/i/Reduced/200418_Li_.00000103.Entered_Coordinates.FIT", "/net/dataserver3/data/users/sterrenwacht/obslog/200418/STL-6303E/i/Reduced/200418_Li_.00000104.Entered_Coordinates.FIT", "/net/dataserver3/data/users/sterrenwacht/obslog/200418/STL-6303E/i/Reduced/200418_Li_.00000105.Entered_Coordinates.FIT"]
        #files = ["/net/dataserver3/data/users/sterrenwacht/obslog/200418/STL-6303E/i/Reduced/200418_Li_.00000081.M_13.FIT", "/net/dataserver3/data/users/sterrenwacht/obslog/200418/STL-6303E/i/Reduced/200418_Li_.00000080.M_13.FIT"]
        print()
    
        # iterate over all the fits files in the specified diretory
        fits_files = filter(self.is_fits, files)
        
        # give the iterable of filenames to the function, which returns a
        # generator, generating pairs containing the finished job and filename.
        result_iter = c.upload_files_gen(fits_files, filter_func=self.enough_sources, filter_args=(10,))
        
        for job, filename in result_iter:
            if not job.success():
                Print("File {} Failed".format(filename), args)
                continue

            # retrieve the wcs file from the successful job
            wcs = job.wcs_file()
            with fits.open(filename) as hdul:
                # append resulting header (with astrometry) to existing header
                hdul[0].header.extend(wcs)

                write_filename = self.change_filename(filename, working_dir)

                Print("Writing to {}...".format(write_filename), args)
                try:
                    hdul.writeto(write_filename)
                except Exception:
                    Print("File {} already exists.".format(write_filename), args)
        
    def on_run_single(self, obs, working_dir, args, file):
        if file not in obs.lightFiles: return
        
        # iterate over all the fits files in the specified diretory
        fits_files = filter(is_fits, files)
        
    def get_reduced_lights(self, working_dir):
        files = []
        save_path = os.path.join(working_dir, cst.reduced_dir)
        for file in os.listdir(save_path):
            if self.is_fits(file):
                files.append(os.path.join(save_path, file))
        return files
        
    def is_fits(self, string):
        """
        Boolean function to test if the extension of the filename provided
        is either .fits or .fit (upper- or lowercase).

        Parameters
        ----------
        string: str
            (path to) filename to test

        Returns
        -------
        bool
        """
        string = string.upper()
        return string.endswith(".FITS") or string.endswith(".FIT")
    

    def change_filename(self, filename, working_dir):
        """
        Generate new filename to avoid overwriting an existing file
        change: ``path/to/file.fits``
        into  : ``path/to/file.astrom.fits``

        Parameters
        ----------
        filename: str
            The full path to the file which is to be changed

        Returns
        -------
        str
            The new path to the given filename
        """
        path, name = os.path.split(filename)
        save_path = os.path.join(working_dir, cst.reduced_dir)
        res_filename = name.split(".")
        res_filename.insert(-1, "astrom")
        res_filename = ".".join(res_filename)
        return os.path.join(save_path, res_filename)
    
    def find_sources(self, filename, detect_threshold=20, fwhm=3):
        with fits.open(filename) as f:
            data = f[0].data
        # find sources
        mean, median, std = sigma_clipped_stats(data, sigma=3.0, maxiters=5)
        daofind = DAOStarFinder(fwhm=fwhm, threshold=detect_threshold * std)
        sources = daofind(data - median)
        return sources


    def enough_sources(self, filename, min_sources=5):
        sources = self.find_sources(filename)
        # terminate if not enough are found.
        # sources is None when no sources are found
        num_sources = len(sources) if sources is not None else 0
        if sources is None or num_sources < min_sources:
            msg = "Not enough sources found: {} found, {} wanted."
            print(msg.format(num_sources, min_sources))
            return False
        print("Found {} sources".format(num_sources))
        return True