from ObservationObject.Observation import Observation

from datetime import datetime
import os
import numpy as np
import csv

import constants_ct as cst
import fits_utils_ct as fut
import utils_ct as ut

def append_pending_log(new_line):
    pd_log = cst.pending_log
    # Create the pending klog if it doesn't exist
    if not os.path.exists(pd_log):
        # Append a header
        clmns = np.array(["Date", "Frame type", "Binning", "Filter", "BIAS-AGE", "DARK-AGE", "FLAT-AGE", "Expires", "Path"])
        np.savetxt(pd_log, clmns.reshape(1, clmns.shape[0]), delimiter=", ", fmt="%s")
        print(f"Created {pd_log}")
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
    present = datetime.now()
    
    if len(lines) == 0:
        ut.Print(f"Pending log empty!", args, True)
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
        print(f"Current line: {line}")
        
        # Check its expiry date if is has one
        try:
            expiry_date = datetime.strptime(line[-2], "%d-%m-%Y")
            if expiry_date.date() < present.date():
                # We cannot hope to find a better version, ever.
                continue
        except ValueError: pass
        
        # Re-reduce a light file
        if frame_type == "Light file":
            # Reinitialise the observation object and working dir
            line_obs = Observation(file_path)
            line_working_dir = (os.path.split(file_path)[0]).replace(cst.tele_path, cst.base_path)
            max_days_off = 365
            # Cut on calculation time if possible
            try:
                max_days_off = abs(max(int(bias_off), int(dark_off), int(flat_off)))
            except ValueError: pass
            # Re-reduce light file. Will add a new entry in the pending log, but hopefully with a
            # lower max_days_off. When the time's there, it will expire.
            fut.reduce_img(line_obs, line_working_dir, args, file_path, max_days_off)
            continue
            
        line_working_dir = os.path.split(file_path)[0].replace(cst.correction_dir, "")
        tele_data_dir = line_working_dir.replace(cst.base_path, cst.tele_path)
        line_obs = Observation(tele_data_dir)
        if frame_type == "Flat file":
            fut.recreate_mflat(line_obs, line_working_dir, args, file_path, binning, fltr)
        if frame_type == "Dark file":
            fut.recreate_mdark(line_obs, line_working_dir, args, file_path, binning, fltr)
            
#         if frame_type == "Dark file" or frame_type == "Flat file":
#             # Recreate the master dark/flat
#             futs.save_correction(obs, working_dir, args, specific_file=filepath.split("/")[-1])
#         elif frame_type == "Light file": 
#             # Re-reduce the light file
#             futs.