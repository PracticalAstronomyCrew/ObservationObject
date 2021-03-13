from astropy.io import fits
from datetime import datetime, timedelta
import numpy as np
import os
import warnings

import core.constants as cst
import core.errors as ers
import core.pending as pd
import core.utils as ut

def get_closest_master(target_datetime, working_dir, max_days_off, binning, frame_type, fltr=""):
    """ Function that returns the closest file to target_datetime, given the
        requirements posed by binning, frametype and possibly fltr. Could for
        example be used to find the closest master Bias to a specific datetime.
        Tries to find potential files within the working_dir first, but extends
        its search range to nearby dates when still no suitable files were found.
        Then, orders the potential files on creation time and returns the closest.
    """
    # Set the filename requirements
    requirements = [frame_type, binning, fltr]
    potential_files = []
    cor_dir = os.path.join(working_dir, cst.correction_dir)
    
    # First, look in the current workspace if there exist suitable files.
    # If yes, add them to a list, which will later be sorted on creation time.
    for filename in os.listdir(cor_dir):
        # Requirements that filename should satisfy
        if not all(req in filename for req in requirements):
            continue
        # File satisfying the requirements found, so add its we add the filepath
        # and its creation time to the potentials list. The third argument, being
        # 0 here, represents the 'relative age' of this frame, see 'days_off'.
        file = os.path.join(cor_dir, filename)
        creation_time = datetime.strptime(fits.getval(file, 'DATE-OBS'), "%Y-%m-%dT%H:%M:%S.%f")
        potential_files.append([file, creation_time, 0])
    
    # If we somehow still don't have any potential master files, we could look 
    # into directories of 'nearby' dates. We increase days_off by 1 each iteration
    # and check both the 'past' and the 'future' folders for suitable files
    folder_date = working_dir.replace(cst.base_path, '').split(os.sep)[1]
    folder_datetime = datetime.strptime(folder_date, '%y%m%d')
    days_off = 1
    while len(potential_files) == 0:
        # Construct the 'future' datefolder corresponding to days_off
        next_cor_date = (folder_datetime + timedelta(days=days_off)).date().strftime('%y%m%d')
        next_cor_dir = cor_dir.replace(folder_date, next_cor_date)

        # If the future dir exists, start looking into its content
        if os.path.exists(next_cor_dir) and os.path.isdir(next_cor_dir):
            for filename in os.listdir(next_cor_dir):
                # Requirements that filename should satisfy
                if not all(req in filename for req in requirements):
                    continue
                # File satisfying the requirements found, so add its we add the filepath
                # and its creation time to the potentials list. The third argument, 
                # 'days_off' keeps track of the relative age of this frame.
                file = os.path.join(next_cor_dir, filename)
                creation_time = datetime.strptime(fits.getval(file, 'DATE-OBS'), "%Y-%m-%dT%H:%M:%S.%f")
                potential_files.append([file, creation_time, days_off])
        
        # Construct the 'past' datefolder corresponding to -days_off
        prev_cor_date = (folder_datetime - timedelta(days=days_off)).date().strftime('%y%m%d')
        prev_cor_dir = cor_dir.replace(folder_date, prev_cor_date)
        
        # If past dir exists, start looking into its content.
        if os.path.exists(prev_cor_dir) and os.path.isdir(prev_cor_dir):
            for filename in os.listdir(prev_cor_dir):
                # Requirements that filename should satisfy
                if not all(req in filename for req in requirements):
                    continue
                # File satisfying the requirements found, so add its we add the filepath
                # and its creation time to the potentials list. The third argument, 
                # 'days_off' keeps track of the relative age of this frame.
                file = os.path.join(prev_cor_dir, filename)
                creation_time = datetime.strptime(fits.getval(file, 'DATE-OBS'), "%Y-%m-%dT%H:%M:%S.%f")
                potential_files.append([file, creation_time, -days_off])
                
        # Increase the search range by one day for next iteration.
        days_off += 1
        
        # Hopefully never happens, but just in case
        if days_off > max_days_off:
            raise ers.SuitableMasterMissingError(
                f"Could not find a suitable {frame_type} of binning {binning}")

    # Sort the potential files on creation time:
    # The files closest to target_datetime, will be the first element.
    closest = min(potential_files, key=lambda file: abs(file[1] - target_datetime))
    closest_master = fits.getdata(closest[0], 0)
    
    # Return the date of the closest master, its path and its days_off.
    return closest_master, closest[0], closest[2]

def header_add_source(header, files):
    header.set(cst.HKW_nsource, str(len(files)))
    for filepath in files:
        ind = files.index(filepath)
        header.set(cst.HKW_source + str(ind+1), str(filepath))
    return header

def header_add_traw(filepath, raw_file):
    fits.setval(filepath, cst.HKW_traw, value=raw_file)

def header_add_praw(filepath, raw_file):
    fits.setval(filepath, cst.HKW_praw, value=raw_file)

def header_add_pred(filepath, red_file):
    fits.setval(filepath, cst.HKW_pred, value=red_file)

def header_add_mbias(header, mbias_path, days_off=None):
    header.set(cst.HKW_mbias, mbias_path)
    if days_off is not None:
        header.set(cst.HKW_mbias_age, days_off)
    return header
    
def header_add_mdark(header, mdark_path, days_off=None):
    header.set(cst.HKW_mdark, mdark_path)
    if days_off is not None:
        header.set(cst.HKW_mdark_age, days_off)
    return header

def header_add_mflat(header, mflat_path, days_off=None):
    header.set(cst.HKW_mflat, mflat_path)
    if days_off is not None:
        header.set(cst.HKW_mflat_age, days_off)
    return header

def save_fits(content, header, save_path):
    """ Takes the content of a fits file and saves it 
        as a new fits file at save_path
    """
    hduNew = fits.PrimaryHDU(content, header=header)
    hduNew.writeto(save_path, overwrite=True)