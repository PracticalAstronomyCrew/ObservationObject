from astropy.io import fits
from datetime import datetime, timedelta
import numpy as np
import os
import warnings

import core.constants as cst
import core.correction as cor
import core.errors as ers
import core.fits_utils as fut
import core.pending as pd
import core.utils as ut
            
def reduce_img(obs, working_dir, args, light_file, max_days_off):
    """ Function that reduces a passed light_file. Tries to find 
        correction frames with a maximum relative age of max_days_off.
    """
    # Retrieve basic information
    binning, fltr, exptime, crtn = obs.get_file_info(light_file, ["BINNING", "FILTER", "EXPTIME", "DATE-OBS"])
    creation_datetime = datetime.strptime(crtn, "%Y-%m-%dT%H:%M:%S.%f")

    # Retrieve the closest master correction frames
    try:
        master_bias, mbias_path, bias_off = fut.get_closest_master(creation_datetime, working_dir, max_days_off,
                                                               binning, "master_bias")
        master_dark, mdark_path, dark_off = fut.get_closest_master(creation_datetime, working_dir, max_days_off,
                                                               binning, "master_dark")
        master_flat, mflat_path, flat_off = fut.get_closest_master(creation_datetime, working_dir, max_days_off,
                                                               binning, "master_flat", fltr=fltr)
    except ers.SuitableMasterMissingError as err:
        warnings.warn(f"Re-reduction failed: {err} for {light_file}")
        # Let's hope the pending log can someday fix this 
        folder_datetime = datetime.strptime(working_dir.replace(cst.base_path, '').split(os.sep)[1], '%y%m%d')
        new_line = np.array([folder_datetime.date(), "Light file", binning, fltr, "?", "?", "?", "-", light_file])
        pd.append_pending_log(new_line)
        return

    # Open the content of the current light fits
    hduList = fits.open(light_file)
    hdu_data = hduList[0].data

    # Add source files to the header
    header = fits.getheader(light_file)
    header = fut.header_add_mbias(header, mbias_path, days_off=bias_off)
    header = fut.header_add_mdark(header, mdark_path, days_off=dark_off)
    header = fut.header_add_mflat(header, mflat_path, days_off=flat_off)

    # Reduce the content and save it
    hdu_data_red = (hdu_data - master_bias - master_dark*exptime) / master_flat
    filename_ori = os.path.basename(light_file)
    red_dir = os.path.join(working_dir, cst.reduced_dir)
    savepath = os.path.join(red_dir, filename_ori)
    fut.save_fits(hdu_data_red, header, savepath)
    ut.Print(f"{savepath} created", args)
    
    # Add an entry to the raw pipeline file pointing towards the current file
    fut.header_add_traw(savepath, light_file)
    # Find the raw version in the backup folder and add the current file to its pred
    backup_rfile = savepath.replace(cst.reduced_dir, cst.raw_dir)
    fut.header_add_pred(backup_rfile, savepath)
    # Also add this raw version to the pipeline reduced file
    fut.header_add_praw(savepath, backup_rfile)

    # Add to the pending log if need be
    max_off = abs(max(bias_off, dark_off, flat_off))
    if max_off > 0:
        folder_datetime = datetime.strptime(working_dir.replace(cst.base_path, '').split(os.sep)[1], '%y%m%d')
        new_line = np.array([folder_datetime.date(), "Light file", binning, fltr, bias_off, dark_off, flat_off, 
                             (folder_datetime + timedelta(days=max_off)).date(), light_file])
        pd.append_pending_log(new_line)
        
def reduce_imgs(obs, working_dir, args):
    """ Wrapper function that loops over every light file and calls
        reduce_img() to do the actual reduction process on a per file
        basis.
    """
    # Initiliase or create the saving dir for reduced content
    red_dir = os.path.join(working_dir, cst.reduced_dir)
    if not os.path.isdir(red_dir): os.mkdir(red_dir)

    # Get basic information about this observation
    lightFiles = sorted(obs.lightFiles, key=lambda file: datetime.strptime(fits.getval(file, 'DATE-OBS'), "%Y-%m-%dT%H:%M:%S.%f"))
    
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
    
    # Loop over every light file in the target
    for light_file in lightFiles:
        reduce_img(obs, working_dir, args, light_file, 365)