from astropy.io import fits
from datetime import datetime, timedelta
import numpy as np
import os
import warnings

import core.constants as cst
import core.errors as ers
import core.fits_utils as fut
import core.pending as pd
import core.utils as ut

def create_mbias(obs, working_dir, args, b_cluster, index):
    """ Function that creates the master bias for a specified b_cluster for 
        the passed Observation Object. This function wraps the Observation
        Object's create_master_bias method, to construct a master bias which 
        corresponds to the passed cluster. The newly generated master bias 
        is directly saved within this function. Note that also a header is 
        added to the master bias, which is a direct copy of the header from 
        the final frame of this bias cluster.
    """
    # Get additional info
    binning, fltr = obs.get_file_info(b_cluster[-1], ["BINNING", "FILTER"])
    
    # Generate the master bias
    mbias = obs.create_master_bias(b_cluster)

    # Add source files to the header
    header = fits.getheader(b_cluster[-1])
    header = fut.header_add_source(header, b_cluster)
    
    # Save the master bias and the updated header
    filename = "master_bias" + binning + "C" + str(index+1) + ".fits"
    cor_dir = os.path.join(working_dir, cst.correction_dir)
    savepath = os.path.join(cor_dir, filename)
    fut.save_fits(mbias, header, savepath)
    ut.Print(f"{savepath} created", args)
    
def create_mdark(obs, working_dir, args, d_cluster, index, max_days_off=365):
    """ Function that creates the master bias for a specified d_cluster for 
        the passed Observation Object. This function wraps the Observation
        Object's create_master_dark method, to construct a master dark which 
        corresponds to the passed cluster. The newly generated master dark 
        is directly saved within this function. Note that also a header is 
        added to the master dark, which is a direct copy of the header from 
        the final frame of this bias cluster. The master bias file used for
        reduction is the closest bias frame that can be found, up to 
        max_days_off days from the current working_dir.
    """
    # Get additional info
    binning, fltr = obs.get_file_info(d_cluster[-1], ["BINNING", "FILTER"])
    
    # Find the closest master bias to the dark creation time
    dark_creation = datetime.strptime(fits.getval(d_cluster[-1], 'DATE-OBS'), "%Y-%m-%dT%H:%M:%S.%f")
    try:
        closest_mbias, mbias_path, bias_off = fut.get_closest_master(dark_creation, working_dir,
                                                                   max_days_off, binning, "master_bias")
    except ers.SuitableMasterMissingError as err:
        warnings.warn(f"Master dark creation failed: {err} for {working_dir}")

        # Let's hope the pending log can someday fix this 
        new_line = np.array([dark_creation.date(), "Dark file", binning, fltr, "?", "-", "-", "-", d_cluster[0]])
        pd.append_pending_log(new_line)
        return
    
    # Generate the master dark using the found master bias
    mdark = obs.create_master_dark(d_cluster, closest_mbias)
    
    # Add source files to the header
    header = fits.getheader(d_cluster[-1])
    header = fut.header_add_source(header, d_cluster)
    header = fut.header_add_mbias(header, mbias_path, days_off=bias_off)

    # Save the master dark and the updated header
    filename = "master_dark" + binning + "C" + str(index+1) + ".fits"
    cor_dir = os.path.join(working_dir, cst.correction_dir)
    savepath = os.path.join(cor_dir, filename)
    fut.save_fits(mdark, header, savepath)
    ut.Print(f"{savepath} created", args)

    # Add to the pending log if need be
    max_off = abs(bias_off)
    if max_off > 0:
        folder_datetime = datetime.strptime(working_dir.replace(cst.base_path, '').split(os.sep)[1], '%y%m%d')
        new_line = np.array([folder_datetime.date(), "Dark file", binning, fltr, bias_off, "-", "-",
                             (folder_datetime + timedelta(days=max_off)).date(), savepath])
        pd.append_pending_log(new_line)
        
def create_mflat(obs, working_dir, args, f_cluster, fltr, index, max_days_off=365):
    """ Function that creates the master bias for a specified d_cluster for 
        the passed Observation Object. This function wraps the Observation
        Object's create_master_dark method, to construct a master dark which 
        corresponds to the passed cluster. The newly generated master dark 
        is directly saved within this function. Note that also a header is 
        added to the master dark, which is a direct copy of the header from 
        the final frame of this bias cluster. The master bias and dark files
        used for reduction are the closest frame that can be found, up to 
        max_days_off days from the current working_dir.
    """
    # Get additional info
    binning, fltr = obs.get_file_info(f_cluster[-1], ["BINNING", "FILTER"])
    
    # Find the closest master bias and master dark to the flat creation time
    flat_creation = datetime.strptime(fits.getval(f_cluster[-1], 'DATE-OBS'), "%Y-%m-%dT%H:%M:%S.%f")
    try:
        closest_mbias, mbias_path, bias_off = fut.get_closest_master(flat_creation, working_dir, max_days_off,
                                                                        binning, "master_bias")
        closest_mdark, mdark_path, dark_off = fut.get_closest_master(flat_creation, working_dir, max_days_off,
                                                                        binning, "master_dark")
    except ers.SuitableMasterMissingError as err:
        warnings.warn(f"Master flat creation failed: {err} for {working_dir}")

        # Let's hope the pending log can someday fix this 
        new_line = np.array([flat_creation.date(), "Flat file", binning, fltr, "?", "?", "-", "-", f_cluster[0]])
        pd.append_pending_log(new_line)
        return
    
    # Generate the master flat using the found master bias and master dark
    mflat = obs.create_master_flats(f_cluster, [fltr], closest_mbias, closest_mdark)
    
    # Add source files to the header
    header = fits.getheader(f_cluster[-1])
    header = fut.header_add_source(header, f_cluster)
    header = fut.header_add_mbias(header, mbias_path, days_off=bias_off)
    header = fut.header_add_mdark(header, mdark_path, days_off=dark_off)

    # Save the master flat and the updated header
    filename = "master_flat" + binning + fltr + "C" + str(index+1) + ".fits"
    cor_dir = os.path.join(working_dir, cst.correction_dir)
    savepath = os.path.join(cor_dir, filename)
    fut.save_fits(mflat, header, savepath)
    ut.Print(f"{savepath} created", args)

    # Add to the pending log if need be
    max_off = abs(max(bias_off, dark_off))
    if max_off > 0:
        folder_datetime = datetime.strptime(working_dir.replace(cst.base_path, '').split(os.sep)[1], '%y%m%d')
        new_line = np.array([folder_datetime.date(), "Flat file", binning, fltr, bias_off, dark_off, "-", 
                             (folder_datetime + timedelta(days=max_off)).date(), savepath])
        pd.append_pending_log(new_line)
            
def save_correction(obs, working_dir, args):
    """ Function that generates and saves all possible master correction 
        frames, for each cluster, binning and filter. Keep in mind that a
        cluster is a group of files that belong together, when consecutive
        frames are taken less than 60min apart from each other.
    """
    # Initiliase or create the saving dir for raw frames
    cor_dir = os.path.join(working_dir, cst.correction_dir)
    if not os.path.isdir(cor_dir): os.mkdir(cor_dir)
        
    # Get the unique binnings/filters for this observation
    binnings = obs.get_binnings(obs.lightFiles)
    fltrs = obs.get_filters(obs.flatFiles)
    
    # Loop over every possible binning
    for binning in binnings:
        # Handle the master bias
        b_clusters = obs.get_bias_clusters(binning)
        for b_cluster in b_clusters:
            create_mbias(obs, working_dir, args, b_cluster, b_clusters.index(b_cluster))
            
        # Handle the master dark
        d_clusters = obs.get_dark_clusters(binning)
        for d_cluster in d_clusters:
            create_mdark(obs, working_dir, args, d_cluster, d_clusters.index(d_cluster))
            
        # Handle the master flats
        # First, loop over every filter
        for fltr in fltrs:
            f_clusters = obs.get_flat_clusters(binning, fltr)
            for f_cluster in f_clusters:
                create_mflat(obs, working_dir, args, f_cluster, fltr, f_clusters.index(f_cluster))
                
        
def recreate_mdark(obs, working_dir, args, file_path, binning, fltr):
    """ Function that recreates the environment needed to re-reduce the 
        dark file located at file_path. Used only in the pending mechanism.
    """
    # Re-initialise basic information
    cor_dir, filename = os.path.split(file_path)
    filename = filename.split(".")[0]
    cluster = filename.replace("master_dark", "").replace(binning, "")
    cluster_index = int(cluster.replace("C", "")) - 1
    
    # Handle the master dark
    d_clusters = obs.get_dark_clusters(binning)
    create_mdark(obs, working_dir, args, d_clusters[cluster_index], cluster_index)
                
def recreate_mflat(obs, working_dir, args, file_path, binning, fltr):
    """ Function that recreates the environment needed to re-reduce the 
        flat file located at file_path. Used only in the pending mechanism.
    """
    # Re-initialise basic information
    cor_dir, filename = os.path.split(file_path)
    filename = filename.split(".")[0]
    cluster = filename.replace("master_dark", "").replace(binning, "").replace(fltr, "")
    cluster_index = int(cluster.replace("C", "")) - 1
    
    f_clusters = obs.get_flat_clusters(binning, fltr)
    create_mflat(obs, working_dir, args, f_clusters[cluster_index], fltr, cluster_index)