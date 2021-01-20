from ObservationObject.Observation import Observation

import os
from shutil import copy2

import constants_ct as cst
import utils_ct as ut

def create_backup(obs, working_dir, args):
    """ Copy all the files in the passed observation object
        to a new directory, like a backup.
    """    
    # Construct the save path
    save_dir = os.path.join(working_dir, cst.raw_dir)
    if not os.path.isdir(save_dir): os.mkdir(save_dir)
    
    # Make a copy of each file
    for file in obs.files:
        copy2(file, save_dir)
        filename = os.path.basename(file)
        ut.Print(f"Copied file to backup: {filename}", args)
        
    return