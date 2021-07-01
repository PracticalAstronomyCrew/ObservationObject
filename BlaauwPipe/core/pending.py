from core.observation import Observation

from datetime import datetime
import os
import numpy as np
import csv

import core.constants as cst
import core.correction as cor
import core.reduction as red

def append_pending_log(new_line):
    pd_log = cst.pending_log
    # Create the pending log if it doesn't exist
    if not os.path.exists(pd_log):
        # Append a header
        clmns = np.array(["Date", "Frame type", "Binning", "Filter", "BIAS-AGE", "DARK-AGE", "FLAT-AGE", "Expires", "Path"])
        np.savetxt(pd_log, clmns.reshape(1, clmns.shape[0]), delimiter=", ", fmt="%s")
    # Append the new line to the pending log
    with open(pd_log, "ab") as f:
        np.savetxt(f, new_line.reshape(1, new_line.shape[0]), delimiter=", ", fmt="%s")
        
def read_pending_log():
    pd_log = cst.pending_log
    lines = []
    # Loop over each line and append its content to the list
    with open(pd_log, "r") as f:
        reader = csv.reader(f, delimiter=",")
        for i, line in enumerate(reader):
            lines.append(line)

    # Note that the first element is the header! This line is purposefully returned
    return lines

def rerun_pending(obs, working_dir, args):
    pd_log = cst.pending_log
    
    # Read the current pending log
    lines = np.array(read_pending_log())
    folder_date = working_dir.replace(cst.base_path, '').split(os.sep)[1]
    folder_datetime = datetime.strptime(folder_date, '%y%m%d')
    
    if len(lines) == 0:
        ut.Print("Pending log empty!", args, True)
        return
    
    # Overwrite the pending log
    with open(pd_log, "wb") as f:
        # Re-append the header
        np.savetxt(f, lines[0].reshape(1, lines[0].shape[0]), delimiter=",", fmt="%s")
    
    # Loop over every old line and check if it needs to be re-run 
    for line in lines[1:]:
        line = np.array([entry.strip() for entry in line])
        # Unpack data and rerun the reduction process
        date, frame_type, binning, fltr, bias_off, dark_off, flat_off, expiry, file_path = line
        
        # Reinitialise the observation object and working dir
        line_obs = Observation(file_path)
        line_working_dir = (os.path.split(file_path)[0]).replace(cst.tele_path, cst.base_path)
        tele_data_dir = line_working_dir.replace(cst.base_path, cst.tele_path)
        
        # Check its expiry date if is has one
        try:
            expiry_date = datetime.strptime(line[-2], "%d-%m-%Y")
            if expiry_date.date() < folder_datetime.date():
                # We cannot hope to find a better version, ever. So, we can 
                # safely continue with new actions/plugins.
                run_plugins_single(line_obs, line_working_dir, args, file, "pending")
        except ValueError: pass
        
        # Re-reduce a light file
        if frame_type == "Light file":
            max_days_off = 365
            # Cut on calculation time if possible
            try:
                max_days_off = abs(max(int(bias_off), int(dark_off), int(flat_off)))
            except ValueError: pass
            # Re-reduce light file. Will add a new entry in the pending log, but hopefully with a
            # lower max_days_off. When the time's there, it will expire.
            red.reduce_img(line_obs, line_working_dir, args, file_path, max_days_off)
        
        # Re-reduce dark frame
        elif frame_type == "Dark file":
            line_working_dir = (os.path.split(os.path.split(file_path)[0])[0]).replace(cst.tele_path, cst.base_path)
            cor.recreate_mdark(line_obs, line_working_dir, args, file_path, binning, fltr)
        # Re-reduce flat field
        elif frame_type == "Flat file":
            line_working_dir = (os.path.split(os.path.split(file_path)[0])[0]).replace(cst.tele_path, cst.base_path)
            cor.recreate_mflat(line_obs, line_working_dir, args, file_path, binning, fltr)