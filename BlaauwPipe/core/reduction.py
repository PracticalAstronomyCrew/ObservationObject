from astropy.io import fits
from datetime import datetime, timedelta
import numpy as np
import os
import warnings

import core.constants as cst
import core.correction as cor
import core.errors as ers
import core.pending as pd
from core.pluginsystem import Plugin
import core.printstatus as ps

import logging
logger = logging.getLogger(__name__)
from blaauwpipe import BlaauwPipe

class Reduction(Plugin):
    def __init__(self):
        super().__init__()
        self.title = "The Fits-Reducer"
        self.call_level = 300
        self.command = "r"
        self.command_full = "reduce"
        self.description = """ Core plugin that uses the previously generated master correction frames
                               stored in cst.cor_dir to reduce the light frames present in the cst.raw_dir
                               directory. Always tries to find the closest (and still compatible) correction
                               frames and if the quality of the image can be improved in the future, this 
                               is noted in the pending_log.
                           """

    def on_run(self, obs, plp):
        self.reduce_imgs(obs, plp)
            
    def reduce_img(self, obs, plp, light_file, max_days_off):
        """ Function that reduces a passed light_file. Tries to find 
            correction frames with a maximum relative age of max_days_off.
        """
        # Retrieve basic information
        binning, fltr, exptime, crtn = plp.get_file_info(light_file, ["BINNING", "FILTER", "EXPTIME", "DATE-OBS"])
        creation_datetime = datetime.strptime(crtn, "%Y-%m-%dT%H:%M:%S.%f")

        # Retrieve the closest master correction frames
        try:
            master_bias, mbias_path, bias_off = BlaauwPipe.get_closest_master(creation_datetime, plp, max_days_off,
                                                                   binning, "master_bias")
            master_dark, mdark_path, dark_off = BlaauwPipe.get_closest_master(creation_datetime, plp, max_days_off,
                                                                   binning, "master_dark")
            master_flat, mflat_path, flat_off = BlaauwPipe.get_closest_master(creation_datetime, plp, max_days_off,
                                                                   binning, "master_flat", fltr=fltr)
        except ers.SuitableMasterMissingError as err:
#             warnings.warn(f"Re-reduction failed: {err} for {light_file}")
            # Let's hope the pending log can someday fix this 
            folder_datetime = datetime.strptime(plp.working_dir.replace(cst.base_path, '').split(os.sep)[1], '%y%m%d')
            new_line = np.array([folder_datetime.date(), "Light file", binning, fltr, "?", "?", "?", "-", light_file])
            pd.append_pending_log(new_line)
            ps.updateFailed(f"Failed to reduce light file ({err}): {light_file}", progressbar=True)
            self.failed_reds += 1
            return

        # Open the content of the current light fits
        hduList = fits.open(light_file)
        hdu_data = hduList[0].data

        # Add source files to the header
        header = fits.getheader(light_file)
        header = BlaauwPipe.header_add_praw(header, light_file) # Add the raw version to this pipeline reduced file
        header = BlaauwPipe.header_add_mbias(header, mbias_path, days_off=bias_off)
        header = BlaauwPipe.header_add_mdark(header, mdark_path, days_off=dark_off)
        header = BlaauwPipe.header_add_mflat(header, mflat_path, days_off=flat_off)

        # Reduce the content and save it
        hdu_data_red = (hdu_data - master_bias - master_dark*exptime) / master_flat
        filename_ori = os.path.basename(light_file)
        savepath = os.path.join(plp.red_dir, filename_ori)
        BlaauwPipe.save_fits(savepath, data=hdu_data_red, header=header)
        
        # Add the current file to the raw version pred
        header = fits.getheader(light_file)
        header = BlaauwPipe.header_add_pred(header, savepath)
        BlaauwPipe.save_fits(light_file, data=hdu_data, header=header)

        # Add to the pending log if need be
        max_off = abs(max(bias_off, dark_off, flat_off))
        if max_off > 0:
            folder_datetime = datetime.strptime(plp.working_dir.replace(cst.base_path, '').split(os.sep)[1], '%y%m%d')
            new_line = np.array([folder_datetime.date(), "Light file", binning, fltr, bias_off, dark_off, flat_off, 
                                 (folder_datetime + timedelta(days=max_off)).date(), light_file])
            pd.append_pending_log(new_line)
            self.failed_reds += 1
            ps.updateWarning(f"Reduced light file with non-zero days-off ({days_off}) saved at {BlaauwPipe.strip_filepath(savepath)}", progressbar=True)
        else:
            ps.updateDone(f"Reduced light file saved at {BlaauwPipe.strip_filepath(savepath)}", progressbar=True)
        ps.newline()
            
        return

    def reduce_imgs(self, obs, plp):
        """ Wrapper function that loops over every light file and calls
            reduce_img() to do the actual reduction process on a per file
            basis.
        """
        # Initiliase or create the saving dir for reduced content
        if not os.path.isdir(plp.red_dir): os.mkdir(plp.red_dir)
            
        ps.done(f"Savepath created at {BlaauwPipe.strip_filepath(plp.red_dir)}")

        # Get basic information about this observation
        lightFiles = sorted(plp.lightFiles, key=lambda file: datetime.strptime(fits.getval(file, 'DATE-OBS'), "%Y-%m-%dT%H:%M:%S.%f"))

    #     # Get the time difference between start and end of the observation
    #     start_time = datetime.strptime(fits.getval(lightFiles[0], 'DATE-OBS'), "%Y-%m-%dT%H:%M:%S.%f")
    #     end_time = datetime.strptime(fits.getval(lightFiles[-1], 'DATE-OBS'), "%Y-%m-%dT%H:%M:%S.%f")
    #     time_diff = end_time - start_time

    #     # This block is not necessary yet, but it starts calculating time-based weights that can 
    #     # be used to construct better master frames by interpolating multiple master biases

    #     # Get the creation time relative to the start of the observation
    #     cr_time_rel = cr_time - start_time

    #     # Creation time scaled between 0 and 1:
    #     # 0 means that it was created at the start;
    #     # 0.5 exactly halfway through the night;
    #     # 1 at the end of the night.
    #     cr_time_scl = cr_time_rel / time_diff

        self.failed_reds = 0
    
        # Loop over every light file in the target
        for light_file in lightFiles:
            filename = os.path.basename(light_file)
            savepath = os.path.join(plp.red_dir, filename)
            ps.progressBar(lightFiles.index(light_file), len(lightFiles), f"Reducing light file: {filename}", log=False)
            self.reduce_img(obs, plp, light_file, 365)
        ps.updateDone(f"Reduction process finished", progressbar=True)
            
        if len(lightFiles) - self.failed_reds > 0:
            ps.done(f"Succesfully reduced {len(lightFiles) - self.failed_reds} light files!")
        if self.failed_reds > 0:
            ps.warning(f"{self.failed_reds} light files were not optimally reduced!")
            