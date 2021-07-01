import core.constants as cst
from core.pluginsystem import Plugin
import core.printstatus as ps

from astrometry_net_client import Client
from astropy.io import fits
from astropy.stats import sigma_clipped_stats
import os
from photutils import DAOStarFinder

import logging
log = logger = logging.getLogger(__name__)
from blaauwpipe import BlaauwPipe

class Astrometry(Plugin):
    def __init__(self):
        super().__init__()
        self.title = "The Astrometry-Uploader"
        self.call_level = 400
        self.command = "a"
        self.command_full = "astrometry"
        self.description = """ Core plugin that uploads (un)reduced light frames to astrometry to retrieve the 
                               exact coordinates the telescope was pointed at. On failure (read: time-out), the
                               light file is appended to the astrometry pending log.
                           """

    def on_run(self, obs, plp):
        self.main(obs, plp)
        #self.create_corrections(obs, plp)

    @staticmethod
    def change_filename(filename, plp):
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
        res_filename = name.split(".")
        res_filename.insert(-1, "astrom")
        res_filename = ".".join(res_filename)
        return os.path.join(plp.red_dir, res_filename)

    @staticmethod
    def find_sources(filename, detect_threshold=20, fwhm=3):
        with fits.open(filename) as f:
            data = f[0].data
        # find sources
        mean, median, std = sigma_clipped_stats(data, sigma=3.0, maxiters=5)
        daofind = DAOStarFinder(fwhm=fwhm, threshold=detect_threshold * std)
        sources = daofind(data - median)
        return sources

    @staticmethod
    def enough_sources(filename, min_sources=5):
        sources = self.find_sources(filename)
        # terminate if not enough are found.
        # sources is None when no sources are found
        num_sources = len(sources) if sources is not None else 0
        if sources is None or num_sources < min_sources:
            msg = "{}: Not enough sources found: {} found, {} wanted."
            print(msg.format(filename, num_sources, min_sources))
            return False
        print("{}: Found {} sources".format(filename, num_sources))
        return True

    def main(self, obs, plp):
        ps.running("Initializing client...")
        c = Client(api_key=cst.api_key)
        ps.updateDone("Logged into Astrometry")

        # set view field width in this range (15-30 arcmin)
        # WARNING: this can be very different for your application.
        c.settings.set_scale_range(15, 30)
        #c.settings.use_sextractor = True

        # Get the raw & corresponding reduced files
        fits_files = plp.red_files[:3]

        # give the iterable of filenames to the function, which returns a
        # generator, generating pairs containing the finished job and filename.
        ps.running("Preparing files for uploading...")
        result_iter = c.upload_files_gen(fits_files)#, filter_func=self.enough_sources)
        ps.updateDone("Light files are ready for Astrometry")

        file_counter = 0
        success_counter = 0
        
        for job, filename in result_iter:
            if not job.success():
                file_counter += 1
                ps.progressBar(file_counter, len(fits_files), f"Astrometry failed for {BlaauwPipe.strip_filepath(filename)}")
                ps.newline()
                continue

            # retrieve the wcs file from the successful job
            wcs = job.wcs_file()
            file_counter += 1
            success_counter += 1
            ps.progressBar(file_counter, len(fits_files), f"Received WCS for {BlaauwPipe.strip_filepath(filename)}")
            ps.newline()
            
            with fits.open(filename) as hdul:
                # append resulting header (with astrometry) to existing header
                hdul[0].header.extend(wcs)

                astrom_file = self.change_filename(filename, plp)
                ps.running(f"Writing to {BlaauwPipe.strip_filepath(astrom_file)}...")
                hdul.writeto(astrom_file)
                ps.updateDone(f"Astrometry results are saved to {BlaauwPipe.strip_filepath(astrom_file)}")
                            
        if success_counter > 0:
            ps.done(f"{success_counter} files were successfully run through Astrometry!")
        if file_counter-success_counter > 0:
            ps.warning(f"{file_counter-success_counter} files could not be resolved!")
        