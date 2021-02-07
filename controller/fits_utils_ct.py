from ObservationObject.Observation import Observation

from astropy.io import fits
from datetime import datetime, timedelta
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

def get_file_clusters(files, step=3600):
    """ Function that splits the past list of files into two/three
        new lists, based on their creation time. The grouped files 
        represent the early and late sets of correction frames, and
        possibly files taken in between.
    """    
    # Sort the files on creation time
    files_sorted = sorted(files, key=lambda file: datetime.strptime(fits.getval(file, 'DATE-OBS'), "%Y-%m-%dT%H:%M:%S.%f"))
    
    # Track the indices where a step takes place
    step_inds = []
    
    # Loop over each file and compare the creation time to the previous
    prev_creation = datetime.strptime(fits.getval(files[0], 'DATE-OBS'), "%Y-%m-%dT%H:%M:%S.%f")
    for file in files_sorted:
        creation_time = datetime.strptime(fits.getval(file, 'DATE-OBS'), "%Y-%m-%dT%H:%M:%S.%f")
        
        # Split the list in two if the time difference is high enough
        if (creation_time - prev_creation).total_seconds() > step:
            step_inds.append(files.index(file))
            
        # Update for next iteration
        prev_creation = creation_time
        
    # No splits, so only one cluster
    if len(step_inds) == 0:
        return [files_sorted]
    
    # Group the clusters together, then return them
    else:
        clusters = []
        # Cluster 1
        clusters.append(files_sorted[:step_inds[0]])
        # Clusters 1 to N-1
        for ind in range(len(step_inds)-1):
            clusters.append(files_sorted[step_inds[ind]:step_inds[ind+1]])
        # Cluster N
        clusters.append(files_sorted[step_inds[-1]:])
        return clusters
    
def get_closest_master(target_datetime, binning, working_dir, frame_type, fltr=""):
    """ Function that returns the closest file to target_datetime, given the
        restrictions by binning and frametype. Could for example be used to
        find the closest master Bias to a specific datetime. Tries to find 
        potential files within the working_dir first, but extends its search 
        range to neabry dates when still no suitable files were found. Then,
        orders the potential files on creation time and returns the closest.
    """
    required = [frame_type, binning, fltr]
    potential_files = []
    cor_dir = os.path.join(working_dir, cst.correction_dir)
    
    # First, look in the current workspace if there exist suitable files.
    # If yes, add them to a list, which will later be sorted on creation time
    for filename in os.listdir(cor_dir):
        # Requirements that filename should satisfy
        if not all(req in filename for req in required):
            continue
        # Potential file found, so add its creation time to potentials list
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
        # Construct the next two dates and their folders
        next_cor_date = (folder_datetime + timedelta(days=days_off)).date().strftime('%y%m%d')
        next_cor_dir = cor_dir.replace(folder_date, next_cor_date)
        prev_cor_date = (folder_datetime - timedelta(days=days_off)).date().strftime('%y%m%d')
        prev_cor_dir = cor_dir.replace(folder_date, prev_cor_date)
                
        # If dir1 exists, start looking into its content
        if os.path.exists(next_cor_dir) and os.path.isdir(next_cor_dir):
            for filename in os.listdir(next_cor_dir):
                # Requirements that filename should satisfy
                if not all(req in filename for req in required):
                    continue
                # Potential file found, so add its creation time to potentials list
                file = os.path.join(next_cor_dir, filename)
                creation_time = datetime.strptime(fits.getval(file, 'DATE-OBS'), "%Y-%m-%dT%H:%M:%S.%f")
                potential_files.append([file, creation_time, days_off])
                
        # If dir2 exists, start looking into its content
        if os.path.exists(prev_cor_dir) and os.path.isdir(prev_cor_dir):
            for filename in os.listdir(prev_cor_dir):
                # Requirements that filename should satisfy
                if not all(req in filename for req in required):
                    continue
                # Potential file found, so add its creation time to potentials list
                file = os.path.join(prev_cor_dir, filename)
                creation_time = datetime.strptime(fits.getval(file, 'DATE-OBS'), "%Y-%m-%dT%H:%M:%S.%f")
                potential_files.append([file, creation_time, days_off])
        # Increase the search range if necessary
        days_off += 1
        
        # Probably never happens, but just in case
        if days_off > 3:
            raise ers.SuitableMasterMissingError(
                f"Could not find a suitable {frame_type} of binning {binning} for {working_dir}")

    # Sort the potential files on creation time:
    # The files closest to target_datetime, will be the first element
    closest = min(potential_files, key=lambda file: abs(file[1] - target_datetime))
    closest_master = fits.getdata(closest[0], 0)
    
    return closest_master, closest[0], closest[2]
        
def get_master_bias(obs, binning):
    """ Function that creates the master dark for a specified binning for 
        the passed Observation Object. When split is set to True, it will 
        generate two/three master Biases: one for the bias frames taken in
        the early night, one for the frames taken at the end of the night
        and possibly one for frames taken in between.
    """
    bias_condit = {"IMAGETYP": "Bias Frame", "BINNING": binning}
    bias_files = obs.get_files(condit=bias_condit)
    
    all_mbias = []
    
    # Split the files into clusters
    bias_clusters = get_file_clusters(bias_files)
    # Only keep clusters with 5 or more files
    bias_clusters = [cluster for cluster in bias_clusters if len(cluster) >= 5]
   
    # Create the master bias for each cluster
    for bias_cluster in bias_clusters:
        master_bias = obs.create_master_bias(biasFiles=bias_cluster)
        all_mbias.append(master_bias)
    
    return all_mbias, bias_clusters

def get_master_dark(obs, binning, working_dir):
    """ Function that creates the master dark for a specified binning and 
        passed master Bias. However, when the split argument is set to true,
        it creates two master Darks: one for the files taken early, the other
        for the dark frames taken towards the end of the night. In this case, 
        master_bias is interpreted as the early master bias, and master_bias_late
        needs to be specified!
    """
    dark_condit = {"IMAGETYP": "Dark Frame", "BINNING": binning}
    dark_files = obs.get_files(condit=dark_condit)
    
    all_mdark = []
    closest_mbias_paths = []
    
    # Split the files into clusters and create the master dark for each cluster
    dark_clusters = get_file_clusters(dark_files)
    for dark_cluster in dark_clusters:
        dark_creation = datetime.strptime(fits.getval(dark_cluster[-1], 'DATE-OBS'), "%Y-%m-%dT%H:%M:%S.%f")
        closest_mbias, closest_path, bias_off = get_closest_master(dark_creation, binning, working_dir, "master_bias")
        master_dark = obs.create_master_dark(darkFiles=dark_cluster, masterBias=closest_mbias)
        all_mdark.append(master_dark)
        closest_mbias_paths.append(closest_path)
    
    return all_mdark, dark_clusters, closest_mbias_paths

def get_master_flat(obs, binning, fltr, working_dir):
    """ Function that creates the master flats for the specified binning and
        for all found unique filters in the Observation object. The master Bias
        and master Dark are also required for this process. Since the Flat Fields
        are almost always made in the early night, its best to pass the early 
        version of the master Bias and master Dark.
    """
    flat_condit = {"IMAGETYP": "Flat Field", "BINNING": binning, "FILTER": fltr}
    flat_files = obs.get_files(condit=flat_condit)
    
    all_mflat = []
    closest_mbias_paths = []
    closest_mdark_paths = []
    
    # Split the files into clusters and create the master dark for each cluster
    flat_clusters = get_file_clusters(flat_files)
    
    # Create the master flats for the found filters
    for flat_cluster in flat_clusters:
        flat_creation = datetime.strptime(fits.getval(flat_cluster[-1], 'DATE-OBS'), "%Y-%m-%dT%H:%M:%S.%f")
        closest_mbias, closest_path_bias, bias_off = get_closest_master(flat_creation, binning, working_dir, "master_bias")
        closest_mdark, closest_path_dark, dark_off = get_closest_master(flat_creation, binning, working_dir, "master_dark")
        master_flat = obs.create_master_flats(flatFiles=flat_files, filterTypes=[fltr], 
                                              masterBias=closest_mbias, masterDark=closest_mdark)
        all_mflat.append(master_flat)
        closest_mbias_paths.append(closest_path_bias)
        closest_mdark_paths.append(closest_path_dark)
                    
    return all_mflat, flat_clusters, closest_mbias_paths, closest_mdark_paths

def save_correction(obs, working_dir, args):
    # Initiliase or create the saving dir for raw frames
    cor_dir = os.path.join(working_dir, cst.correction_dir)
    if not os.path.isdir(cor_dir): os.mkdir(cor_dir)
        
    # Get the unique binnings for this observation
    binnings = get_binnings(obs, obs.lightFiles)
    
    # Loop over every possible binning
    for binning in binnings:
        # Get the master biases and save them
        all_mbias, bias_clusters = get_master_bias(obs, binning)
        for i in range(len(all_mbias)):
            # Get the master bias and cluster files
            mbias = all_mbias[i]
            bias_cluster = bias_clusters[i]
            # Add origin files to the header
            header = fits.getheader(bias_cluster[-1])
            header = header_add_origin(header, bias_cluster)
            # Save the master bias and the updated header
            filename = "master_bias" + binning + "C" + str(i+1) + ".fits"
            savepath = os.path.join(cor_dir, filename)
            save_fits(mbias, header, savepath)
            ut.Print(f"{savepath} created", args)
        
        # Get the master darks and save them
        all_mdark, dark_clusters, used_mbias = get_master_dark(obs, binning, working_dir)
        for i in range(len(all_mdark)):
            # Get the master bias and cluster files
            mdark = all_mdark[i]
            dark_cluster = dark_clusters[i]
            mbias_path = used_mbias[i]
            # Add origin files to the header
            header = fits.getheader(dark_cluster[-1])
            header = header_add_origin(header, dark_cluster)
            header = header_add_mbias(header, mbias_path)
            # Save the master dark and the updated header
            filename = "master_dark" + binning + "C" + str(i+1) + ".fits"
            savepath = os.path.join(cor_dir, filename)
            save_fits(mdark, header, savepath)
            ut.Print(f"{savepath} created", args)
        
        # Get the flat files for all filters and save them
        flat_condit = {"IMAGETYP": "Flat Field", "BINNING": binning}
        flat_files = obs.get_files(condit=flat_condit)
        fltrs = get_filters(obs, flat_files)
        # First, loop over every filter
        for fltr in fltrs:
            all_mflat, flat_clusters, mbias_paths, mdark_paths = get_master_flat(obs, binning, fltr, working_dir)
            for i in range(len(all_mflat)):
                # Get the master bias, dark and cluster files
                mflat = all_mflat[i]
                flat_cluster = flat_clusters[i]
                mbias_path = mbias_paths[i]
                mdark_path = mdark_paths[i]
                # Add origin files to the header
                header = fits.getheader(flat_cluster[-1])
                header = header_add_origin(header, flat_cluster)
                header = header_add_mbias(header, mbias_path)
                header = header_add_mdark(header, mdark_path)
                # Save the master flat and the updated header
                filename = "master_flat" + binning + fltr + "C" + str(i+1) + ".fits"
                savepath = os.path.join(cor_dir, filename)
                #save_fits(mflat, header, savepath)
                ut.Print(f"{savepath} created", args)
                
    return

def reduce_imgs(obs, working_dir, args):
    # Initiliase or create the saving dir for reduced content
    red_dir = os.path.join(working_dir, cst.reduced_dir)
    if not os.path.isdir(red_dir): os.mkdir(red_dir)

    # Get basic information about this observation
    lightFiles = sorted(obs.lightFiles, key=lambda file: datetime.strptime(fits.getval(file, 'DATE-OBS'), "%Y-%m-%dT%H:%M:%S.%f"))
    binnings = get_binnings(obs, lightFiles)
    filters = get_filters(obs, lightFiles)
    
    # Get the time difference between start and end of the observation
    start_time = datetime.strptime(fits.getval(lightFiles[0], 'DATE-OBS'), "%Y-%m-%dT%H:%M:%S.%f")
    end_time = datetime.strptime(fits.getval(lightFiles[-1], 'DATE-OBS'), "%Y-%m-%dT%H:%M:%S.%f")
    time_diff = end_time - start_time
    
    # Loop over every light file in the target
    for light_file in lightFiles:
        # Retrieve basic information
        binning, fltr, exptime, crtn = obs.get_file_info(light_file, ["BINNING", "FILTER", "EXPTIME", "DATE-OBS"])
        creation_datetime = datetime.strptime(crtn, "%Y-%m-%dT%H:%M:%S.%f")
        
#         # This block is not necessary yet, but it starts calculating time-based weights
#         # that can be used to construct better master frames by combining

#         # Get the creation time relative to the start of the observation
#         cr_time_rel = cr_time - start_time
        
#         # Creation time scaled between 0 and 1:
#         # 0 means that it was created at the start;
#         # 0.5 exactly halfway through the night;
#         # 1 at the end of the night.
#         cr_time_scl = cr_time_rel / time_diff
        
        # Retrieve the closest master correction frames
        master_bias, mbias_path, bias_off = get_closest_master(creation_datetime, binning, working_dir, "master_bias")
        master_dark, mdark_path, dark_off = get_closest_master(creation_datetime, binning, working_dir, "master_dark")
        master_flat, mflat_path, flat_off = get_closest_master(creation_datetime, binning, working_dir, "master_flat", fltr=fltr)
        
        # Open the content of the current fits
        hduList = fits.open(light_file)
        hdu_data = hduList[0].data
        
        # Add origin files to the header
        header = fits.getheader(light_file)
        header = header_add_mbias(header, mbias_path, days_off=bias_off)
        header = header_add_mdark(header, mdark_path, days_off=dark_off)
        header = header_add_mflat(header, mflat_path, days_off=flat_off)

        # Reduce the content and save it
        hdu_data_red = (hdu_data - master_bias - master_dark*exptime) / master_flat
        filename_ori = os.path.basename(light_file)
        savepath = os.path.join(red_dir, filename_ori)
        save_fits(hdu_data_red, header, savepath)
        ut.Print(f"{savepath} created", args)

def header_add_origin(header, files):
    header.set("NORIGIN", str(len(files)))
    for filepath in files:
        ind = files.index(filepath)
        header.set("ORIGIN" + str(ind+1), str(filepath))
    return header

def header_add_mbias(header, mbias_path, days_off=None):
    header.set("M-BIAS", mbias_path)
    if days_off is not None:
        header.set("BIAS-OFF", days_off)
    return header
    
def header_add_mdark(header, mdark_path, days_off=None):
    header.set("M-DARK", mdark_path)
    if days_off is not None:
        header.set("DARK-OFF", days_off)
    return header

def header_add_mflat(header, mflat_path, days_off=None):
    header.set("M-FLAT", mflat_path)
    if days_off is not None:
        header.set("FLAT-OFF", days_off)
    return header

def save_fits(content, header, save_path):
    """ Takes the content of a fits file and saves it 
        as a new fits file at save_path
    """
    hduNew = fits.PrimaryHDU(content, header=header)
    hduNew.writeto(save_path, overwrite=True)