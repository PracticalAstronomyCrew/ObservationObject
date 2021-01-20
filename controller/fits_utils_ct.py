from ObservationObject.Observation import Observation

from astropy.io import fits
import os

import constants_ct as cst
import errors_ct as ers
import utils_ct as ut

def get_binnings(obs, files):
    # Returns all unique binning types for light frames
    binnings = []
    for file in files:
        cur_binning = obs.get_file_info(file, ["BINNING"])[0]
        if cur_binning not in binnings:
            binnings.append(cur_binning)
            
    return binnings

def get_filters(obs, files):
    # Returns all unique filter types for a given list of files
    filters = []
    for file in files:
        cur_filter = obs.get_file_info(file, ["FILTER"])[0]
        if cur_filter not in filters:
            filters.append(cur_filter)
            
    return filters

def get_master_bias(obs, binning):
    bias_condit = {"IMAGETYP": "Bias Frame", "BINNING": binning}
    bias_files = obs.get_files(condit=bias_condit)
    
    # Create the master bias
    if len(bias_files) > 0:
        master_bias = obs.create_master_bias(biasFiles=bias_files)
        return master_bias
    
    return None

def get_master_dark(obs, binning, master_bias):
    dark_condit = {"IMAGETYP": "Dark Frame", "BINNING": binning}
    dark_files = obs.get_files(condit=dark_condit)
    
    # Create and save the master dark
    if len(dark_files) > 0:
        master_dark = obs.create_master_dark(darkFiles=dark_files, masterBias=master_bias)
        return master_dark

    return None

def get_master_flats(obs, binning, master_bias, master_dark):
    flat_condit = {"IMAGETYP": "Flat Field", "BINNING": binning}
    flat_files = obs.get_files(condit=flat_condit)
    file_filters = get_filters(obs, flat_files)
    
    # Create the master flats for the found filters
    if len(flat_files) > 0:
        master_flats = obs.create_master_flats(flatFiles=flat_files, filterTypes=file_filters,
                                               masterBias=master_bias, masterDark=master_dark)
        return master_flats, file_filters
    
    return None, file_filters

def save_correction(obs, working_dir, args):
    # Initiliase or create the saving dir for raw frames
    cor_dir = os.path.join(working_dir, cst.correction_dir)
    if not os.path.isdir(cor_dir): os.mkdir(cor_dir)
        
    # Get the unique binnings for this observation
    binnings = get_binnings(obs, obs.lightFiles)
        
    # Loop over every possible binning
    for binning in binnings:
        # Get the master bias and save it
        master_bias = get_master_bias(obs, binning)
        bias_success = master_bias is not None
        if bias_success:
            filename = "master_bias" + binning + ".fits"
            save_fits(master_bias, os.path.join(cor_dir, filename), args)
        
        # Get the master dark and save it
        master_dark = get_master_dark(obs, binning, master_bias)
        dark_success = master_dark is not None
        if dark_success and bias_success:
            filename = "master_dark" + binning + ".fits"
            save_fits(master_dark, os.path.join(cor_dir, filename), args)
        
        # Get the flat files and save them
        master_flats, file_filters = get_master_flats(obs, binning, master_bias, master_dark)
        flats_success = master_flats is not None
        if flats_success and dark_success and bias_success:
            # Loop over every filter and save the corresponding master flat
            for i in range(master_flats.shape[2]):
                cur_filter = file_filters[i]
                if master_flats.ndim == 2:
                    master_flat = master_flats
                else:
                    master_flat = master_flats[:,:,i]
                filename = "master_flat" + cur_filter + binning + ".fits"
                save_fits(master_flat, os.path.join(cor_dir, filename), args)
                
    return

def reduce_imgs(obs, working_dir, args):
    # Initiliase or create the saving dir for reduced content
    red_dir = os.path.join(working_dir, cst.reduced_dir)
    if not os.path.isdir(red_dir): os.mkdir(red_dir)

    # Get basic information about this observation
    lightFiles = obs.lightFiles
    binnings = get_binnings(obs, lightFiles)
    filters = get_filters(obs, lightFiles)
    
    # Keep track of already used binnings
    # Bit hardcoded, but well, it works (for now)
    bias_1x1 = dark_1x1 = flats_1x1 = None
    bias_3x3 = dark_3x3 = flats_3x3 = None
    
    # Loop over every light file in the target
    for light_file in lightFiles:
        # Retrieve basic information
        binning, fltr, exptime = obs.get_file_info(light_file, ["BINNING", "FILTER", "EXPTIME"])
        
        # Prepare the frames based on their binning
        if binning == "1x1":
            # Check for a cached version, otherwise create new 1x1 frames
            if bias_1x1 is None: bias_1x1 = get_master_bias(obs, binning)
            if dark_1x1 is None: dark_1x1 = get_master_dark(obs, binning, bias_1x1)
            if flats_1x1 is None: flats_1x1, file_filters = get_master_flats(obs, binning, bias_1x1, dark_1x1)
                
            # Prepare the frames
            master_bias = bias_1x1
            master_dark = dark_1x1 * exptime
            if flats_1x1.ndim == 2:
                master_flat = master_flats_1x1
            else:
                master_flat = flats_1x1[:,:,file_filters.index(fltr)]
            
        elif binning == "3x3":
            # Check for a cached version, otherwise create new 3x3 frames
            if bias_3x3 is None: bias_3x3 = get_master_bias(obs, binning)
            if dark_3x3 is None: dark_3x3 = get_master_dark(obs, binning, bias_3x3)
            if flats_3x3 is None: flats_3x3, file_filters = get_master_flats(obs, binning, bias_3x3, dark_3x3)
            
            # Prepare the frames
            master_bias = bias_3x3
            master_dark = dark_3x3 * exptime
            if flats_3x3.ndim == 2:
                master_flat = master_flats_3x3
            else:
                master_flat = flats_3x3[:,:,file_filters.index(fltr)]
            
        else:
            raise ers.UnknownBinningError(f"Encountered unknown binning: {binning}")
            
        # Open the content of the current fits
        hduList = fits.open(light_file)
        hdu_data = hduList[0].data
        
        # Reduce the content and save it
        hdu_data_red = (hdu_data - master_bias - master_dark) / master_flat
        filename_ori = os.path.basename(light_file)
        save_fits(master_flat, os.path.join(red_dir, filename_ori), args)
    
    return

def save_fits(content, save_path, args):
    """ Takes the content of a fits file and saves it 
        as a new fits file at save_path
    """
    # TODO: Add header functionality
    hduNew = fits.PrimaryHDU(content)
    hduNew.writeto(save_path)
    
    ut.Print(f"{save_path} created", args)