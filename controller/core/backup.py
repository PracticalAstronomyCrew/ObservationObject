from astropy.io import fits
from datetime import datetime
import os
from shutil import copy2

import core.constants as cst
import core.fits_utils as fut
import core.utils as ut

def create_backup(obs, working_dir, args):
    """ Copy all the files in the passed observation object
        to a new directory, just like a backup.
    """    
    # Construct the save path
    save_dir = os.path.join(working_dir, cst.raw_dir)
    if not os.path.isdir(save_dir): os.mkdir(save_dir)
    
    # Make a copy of each file
    for ori_file in obs.files:
        copy2(ori_file, save_dir)
        filename = os.path.basename(ori_file)
        filepath = os.path.join(save_dir, filename)
        ut.Print(f"Copied file to backup: {filename}", args)
        
        # Add header keyword TRAW
        fut.header_add_traw(filepath, ori_file)