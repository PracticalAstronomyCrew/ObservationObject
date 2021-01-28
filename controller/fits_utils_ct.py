from ObservationObject.Observation import Observation

from astropy.io import fits
import numpy as np
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

def split_early_late(files, step=2*3600):
    """ Function that splits the past list of files into two new 
        lists, based on their creation time. The grouped files 
        represent the early and late sets of correction frames. 
        The two sets are seperated when a difference of more than
        the specified step is encountered in their creation times.
    """
    # Sort the files on creation time
    files_sorted = sorted(files, key=os.path.getmtime)
    files_early = files_sorted
    files_late = []
    
    # Loop over each file and compare the creation time to the previous
    last_creation = os.path.getmtime(files[0])
    for file in files_sorted:
        creation_time = os.path.getmtime(file)
        
        # Split the list in two if the time difference is high enough
        if creation_time - last_creation > step:
            ind = files.index(file)
            files_early = files[:ind]
            files_late = files[ind:]
            
        # Update for next iteration
        last_creation = creation_time
            
    return files_early, files_late

def get_master_bias(obs, binning, split=False):
    """ Function that creates the master dark for a specified binning for 
        the passed Observation Object. When split is set to True, it will 
        generate two master Biases: one for the bias frames taken in the 
        early night, the other for the frames taken at the end of the night.
    """
    bias_condit = {"IMAGETYP": "Bias Frame", "BINNING": binning}
    bias_files = obs.get_files(condit=bias_condit)
    
    # Create the master bias
    if len(bias_files) > 0:
        if not split:
            master_bias = obs.create_master_bias(biasFiles=bias_files)
            return master_bias
    
        else:
            # Split the files and create the master biases
            early_bias, late_bias = split_early_late(bias_files)
            master_bias_early = obs.create_master_bias(biasFiles=early_bias) if early_bias else None
            master_bias_late = obs.create_master_bias(biasFiles=late_bias) if late_bias else None
            return master_bias_early, master_bias_late, early_bias, late_bias
    
    return None

def get_master_dark(obs, binning, master_bias, split=False, master_bias_late=None):
    """ Function that creates the master dark for a specified binning and 
        passed master Bias. However, when the split argument is set to true,
        it creates two master Darks: one for the files taken early, the other
        for the dark frames taken towards the end of the night. In this case, 
        master_bias is interpreted as the early master bias, and master_bias_late
        needs to be specified!
    """
    dark_condit = {"IMAGETYP": "Dark Frame", "BINNING": binning}
    dark_files = obs.get_files(condit=dark_condit)
    
    # Create and save the master dark
    if len(dark_files) > 0:
        if not split:
            master_dark = obs.create_master_dark(darkFiles=dark_files, masterBias=master_bias)
            return master_dark
    
        # Split the files and create the master darks
        else:
            early_dark, late_dark = split_early_late(dark_files)
            master_dark_early = obs.create_master_dark(darkFiles=early_dark, masterBias=master_bias) if early_dark else None
            master_dark_late = obs.create_master_dark(darkFiles=late_dark, masterBias=master_bias_late) if late_dark else None
            return master_dark_early, master_dark_late, early_dark, late_dark

    return None

def get_master_flats(obs, binning, master_bias, master_dark):
    """ Function that creates the master flats for the specified binning and
        for all found unique filters in the Observation object. The master Bias
        and master Dark are also required for this process. Since the Flat Fields
        are almost always made in the early night, its best to pass the early 
        version of the master Bias and master Dark.
    """
    flat_condit = {"IMAGETYP": "Flat Field", "BINNING": binning}
    flat_files = obs.get_files(condit=flat_condit)
    file_filters = get_filters(obs, flat_files)
    
    # Create the master flats for the found filters
    if len(flat_files) > 0:
        master_flats = None
        fltr_files_lst = []
        for fltr in file_filters:
            fltr_condit = {"IMAGETYP": "Flat Field", "BINNING": binning, "FILTER": fltr}
            fltr_files = obs.get_files(condit=fltr_condit)
            fltr_files_lst.append(fltr_files)
            master_flat = obs.create_master_flats(flatFiles=fltr_files, filterTypes=[fltr],
                                                   masterBias=master_bias, masterDark=master_dark)
            if master_flats is None:
                master_flats = master_flat
            else:
                master_flats = np.dstack((master_flats, master_flat))
                
        return master_flats, file_filters, fltr_files_lst
    
    return None, file_filters, None

def save_correction(obs, working_dir, args):
    # Initiliase or create the saving dir for raw frames
    cor_dir = os.path.join(working_dir, cst.correction_dir)
    if not os.path.isdir(cor_dir): os.mkdir(cor_dir)
        
    # Get the unique binnings for this observation
    binnings = get_binnings(obs, obs.lightFiles)
    
    # Loop over every possible binning
    for binning in binnings:
        # Get the master biases and save them
        mbias_early, mbias_late, early_files, late_files = get_master_bias(obs, binning, split=True)
        if mbias_early is not None:
            header_base = fits.getheader(early_files[-1])
            header_new = header_add_origin(header_base, early_files)
            filename = "master_bias" + binning + "Early.fits"
            save_fits(mbias_early, header_new, os.path.join(cor_dir, filename), args)
        if mbias_late is not None:
            header_base = fits.getheader(early_files[-1])
            header_new = header_add_origin(header_base, late_files)
            filename = "master_bias" + binning + "Late.fits"
            save_fits(mbias_late, header_new, os.path.join(cor_dir, filename), args)
        
        # Get the master darks and save them
        mdark_early, mdark_late, early_files, late_files = get_master_dark(obs, binning, mbias_early,
                                                                           split=True, master_bias_late=mbias_late)
        if mdark_early is not None:
            header_base = fits.getheader(early_files[-1])
            header_new = header_add_origin(header_base, early_files)
            filename = "master_dark" + binning + "Early.fits"
            save_fits(mdark_early, header_new, os.path.join(cor_dir, filename), args)
        if mdark_late is not None:
            header_base = fits.getheader(early_files[-1])
            header_new = header_add_origin(header_base, late_files)
            filename = "master_dark" + binning + "Late.fits"
            save_fits(mdark_late, header_new, os.path.join(cor_dir, filename), args)
            
        # Get the flat files and save them
        mflats, file_filters, fltr_files_lst = get_master_flats(obs, binning, mbias_early, mdark_early)
        if mflats is not None:
            # Loop over every filter and save the corresponding master flat
            for i in range(mflats.shape[2]):
                cur_filter = file_filters[i]
                cur_files = fltr_files_lst[i]
                if mflats.ndim == 2:
                    mflat = mflats
                else:
                    mflat = mflats[:,:,i]
                header_base = fits.getheader(cur_files[-1])
                header_new = header_add_origin(header_base, cur_files)
                filename = "master_flat" + binning + cur_filter + ".fits"
                save_fits(mflat, header_new, os.path.join(cor_dir, filename), args)
                
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

def header_add_origin(header, files):
    header.set("NORIGIN", str(len(files)))
    for filepath in files:
        ind = files.index(filepath)
        header.set("ORIGIN" + str(ind+1), str(filepath))
    return header

def save_fits(content, header, save_path, args):
    """ Takes the content of a fits file and saves it 
        as a new fits file at save_path
    """
    # TODO: Add header functionality
    hduNew = fits.PrimaryHDU(content, header=header)
    hduNew.writeto(save_path)
#     header.tofile(save_path)
#     fits.writeto(save_path, hduNew, header)
    
    ut.Print(f"{save_path} created", args)