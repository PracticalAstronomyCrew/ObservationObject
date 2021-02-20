from ObservationObject.Observation import Observation

from astropy.io import fits
from datetime import datetime, timedelta
import numpy as np
import os
import warnings

import constants_ct as cst
import errors_ct as ers
import pending_ct as pd
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
    """ Function that splits the passed list of files into clusters.
        Clusters are groups of files that belong together, because 
        they were taken shortly after each other. If the creation time
        difference between two adjacent files in the sorted list is 
        greater than step seconds, then the newest file comes into a 
        different cluster. Most of the time, there'll be two clusters, 
        corresponding to the early and late correction frames. One might 
        also encounter three clusters. In this case, an extra set of 
        frames was probably taken halfway through the observation.
    """    
    # Sort the files on creation time
    files_sorted = sorted(files, key=lambda file: datetime.strptime(fits.getval(file, 'DATE-OBS'), "%Y-%m-%dT%H:%M:%S.%f"))
    
    # Track the indices where a step takes place
    step_inds = []
    
    # Loop over each file and compare the creation time to the previous
    prev_creation = datetime.strptime(fits.getval(files[0], 'DATE-OBS'), "%Y-%m-%dT%H:%M:%S.%f")
    for file in files_sorted:
        creation_time = datetime.strptime(fits.getval(file, 'DATE-OBS'), "%Y-%m-%dT%H:%M:%S.%f")
        
        # Store the current index if the time difference is high enough
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
    
def get_closest_master(target_datetime, working_dir, binning, frame_type, fltr="", max_days_off=365):
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
        
def get_master_bias(obs, binning):
    """ Function that creates the master bias for a specified binning for 
        the passed Observation Object. This function wraps the Observation
        Object's create_master_bias method, to also take care of different 
        clusters. Returns the master biases for all found clusters in the 
        multidimensional array all_mbias, and also returns the found bias 
        clusters stored in bias_clusters.
    """
    # Get suitable bias frames
    bias_condit = {"IMAGETYP": "Bias Frame", "BINNING": binning}
    bias_files = obs.get_files(condit=bias_condit)
    
    # Used for storing all master biases
    all_mbias = []
    
    # We might have caught nothing
    if len(bias_files) == 0:
        return [], []
    
    # Split the files into clusters
    bias_clusters = get_file_clusters(bias_files)
    # Only keep clusters with 5 or more files
    bias_clusters = [cluster for cluster in bias_clusters if len(cluster) >= 5]
   
    # Create the master bias for each cluster
    for bias_cluster in bias_clusters:
        # Generate the master bias
        master_bias = obs.create_master_bias(biasFiles=bias_cluster)
        all_mbias.append(master_bias)
    
    return all_mbias, bias_clusters

def get_master_dark(obs, binning, working_dir, cluster=None, max_days_off=365):
    """ Function that creates the master bias for a specified binning for 
        the passed Observation Object. This function wraps the Observation
        Object's create_master_dark method, to also take care of different 
        clusters. Furthermore, it automatically finds the best master bias 
        that should be used for the bias reduction. Returns the master darks
        for all found clusters in the multidimensional array all_mdark, also
        returns the found dark clusters stored in dark_clusters, and a list 
        of the closest master bias paths, one for each dark frame cluster.
    """
    # Get suitable dark frames
    dark_condit = {"IMAGETYP": "Dark Frame", "BINNING": binning}
    dark_files = obs.get_files(condit=dark_condit)
    
    # Used for storing all master biases
    all_mdark = []
    closest_mbias_paths = []
    biases_off = []
    
    # We might have caught nothing
    if len(dark_files) == 0:
        return [], []
    
    # Split the files into clusters and create the master dark for each cluster
    dark_clusters = get_file_clusters(dark_files)
    if cluster is not None: dark_clusters = [dark_clusters[cluster]]
    for dark_cluster in dark_clusters:
        # Find the closest master bias to the dark creation time
        dark_creation = datetime.strptime(fits.getval(dark_cluster[-1], 'DATE-OBS'), "%Y-%m-%dT%H:%M:%S.%f")
        try:
            closest_mbias, closest_path, bias_off = get_closest_master(dark_creation, working_dir, binning,
                                                                       "master_bias", max_days_off=max_days_off)
        except ers.SuitableMasterMissingError as err:
            warnings.warn(f"Master dark creation failed: {err} for {working_dir}")
            all_mdark.append(np.array([]))
            closest_mbias_paths.append("")
            biases_off.append("")
            
            # Let's hope the pending log can someday fix this 
            new_line = np.array([creation_datetime.date(), "Dark file", binning, fltr, "?", "-", "-", "-", dark_cluster[0]])
            pd.append_pending_log(new_line)
            continue
            
        # Generate the master dark using the found master bias
        master_dark = obs.create_master_dark(darkFiles=dark_cluster, masterBias=closest_mbias)
        all_mdark.append(master_dark)
        closest_mbias_paths.append(closest_path)
        biases_off.append(bias_off)
    
    return all_mdark, dark_clusters, closest_mbias_paths, biases_off

def get_master_flat(obs, binning, fltr, working_dir, cluster=None, max_days_off=365):
    """ Function that creates the master flat for a specified binning and
        filter for the passed Observation Object. This function wraps the
        Observation Object's create_master_flat method, to also take care
        of different clusters. Furthermore, it automatically finds the best
        master bias and master dark that should be used for the bias and 
        dark reduction. Returns the master flat for all found clusters in
        the multidimensional array all_mflat, also returns the found flat
        clusters stored in flat_clusters, and a list of the closest master
        bias and master dark paths, one couple for each flat fields cluster.
    """
    # Get suitable flat fields
    flat_condit = {"IMAGETYP": "Flat Field", "BINNING": binning, "FILTER": fltr}
    flat_files = obs.get_files(condit=flat_condit)

    # Used for storing all master flats
    all_mflat = []
    closest_mbias_paths = []
    closest_mdark_paths = []
    biases_off = []
    darks_off = []

    # We might have caught nothing
    if len(flat_files) == 0:
        return [], []
    
    # Split the files into clusters and create the master dark for each cluster
    flat_clusters = get_file_clusters(flat_files)
    if cluster is not None: flat_clusters = [flat_clusters[cluster]]
    # Create the master flats for the found filters
    for flat_cluster in flat_clusters:
        # Find the closest master bias and master dark to the flat creation time
        flat_creation = datetime.strptime(fits.getval(flat_cluster[-1], 'DATE-OBS'), "%Y-%m-%dT%H:%M:%S.%f")
        try:
            closest_mbias, closest_path_bias, bias_off = get_closest_master(flat_creation, working_dir, binning,
                                                                            "master_bias", max_days_off=max_days_off)
            closest_mdark, closest_path_dark, dark_off = get_closest_master(flat_creation, working_dir, binning,
                                                                            "master_dark", max_days_off=max_days_off)
        except ers.SuitableMasterMissingError as err:
            warnings.warn(f"Master flat creation failed: {err} for {working_dir}")
            all_mflat.append(np.array([]))
            closest_mbias_paths.append("")
            closest_mdark_paths.append("")
            biases_off.append("")
            darks_off.append("")
            
            # Let's hope the pending log can someday fix this 
            new_line = np.array([creation_datetime.date(), "Flat file", binning, fltr, "?", "?", "-", "-", flat_cluster[0]])
            pd.append_pending_log(new_line)
            continue
            
        # Generate the master flat using the found master bias and master dark
        master_flat = obs.create_master_flats(flatFiles=flat_files, filterTypes=[fltr], 
                                              masterBias=closest_mbias, masterDark=closest_mdark)
        all_mflat.append(master_flat)
        closest_mbias_paths.append(closest_path_bias)
        closest_mdark_paths.append(closest_path_dark)
        biases_off.append(bias_off)
        darks_off.append(dark_off)
                    
    return all_mflat, flat_clusters, closest_mbias_paths, closest_mdark_paths, biases_off, darks_off

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
        all_mdark, dark_clusters, used_mbias, biases_off = get_master_dark(obs, binning, working_dir)
        for i in range(len(all_mdark)):
            # Get the master bias and cluster files
            mdark = all_mdark[i]
            dark_cluster = dark_clusters[i]
            mbias_path = used_mbias[i]
            bias_off = biases_off[i]
            
            # Master dark creation failed.
            if mdark.size == 0:
                continue
            
            # Add origin files to the header
            header = fits.getheader(dark_cluster[-1])
            header = header_add_origin(header, dark_cluster)
            header = header_add_mbias(header, mbias_path, days_off=bias_off)

            # Save the master dark and the updated header
            filename = "master_dark" + binning + "C" + str(i+1) + ".fits"
            savepath = os.path.join(cor_dir, filename)
            save_fits(mdark, header, savepath)
            ut.Print(f"{savepath} created", args)
                      
            # Add to the pending log if need be
            max_off = abs(bias_off)
            if max_off > 0:
                folder_datetime = datetime.strptime(working_dir.replace(cst.base_path, '').split(os.sep)[1], '%y%m%d')
                new_line = np.array([folder_datetime.date(), "Dark file", binning, fltr, bias_off, "-", "-",
                                     (folder_datetime + timedelta(days=max_off)).date(), savepath])
                pd.append_pending_log(new_line)
        
        # Get the flat files for all filters and save them
        flat_condit = {"IMAGETYP": "Flat Field", "BINNING": binning}
        flat_files = obs.get_files(condit=flat_condit)
        fltrs = get_filters(obs, flat_files)
        # First, loop over every filter
        for fltr in fltrs:
            all_mflat, flat_clusters, mbias_paths, mdark_paths, biases_off, darks_off = get_master_flat(obs, binning, fltr, working_dir)
            for i in range(len(all_mflat)):
                # Get the master bias, dark and cluster files
                mflat = all_mflat[i]
                flat_cluster = flat_clusters[i]
                mbias_path = mbias_paths[i]
                mdark_path = mdark_paths[i]
                bias_off = biases_off[i]
                dark_off = darks_off[i]
                
                # Master flat creation failed.
                if mflat.size == 0:
                    continue
                
                # Add origin files to the header
                header = fits.getheader(flat_cluster[-1])
                header = header_add_origin(header, flat_cluster)
                header = header_add_mbias(header, mbias_path, days_off=bias_off)
                header = header_add_mdark(header, mdark_path, days_off=dark_off)
                
                # Save the master flat and the updated header
                filename = "master_flat" + binning + fltr + "C" + str(i+1) + ".fits"
                savepath = os.path.join(cor_dir, filename)
                save_fits(mflat, header, savepath)
                ut.Print(f"{savepath} created", args)
                
                # Add to the pending log if need be
                max_off = abs(max(bias_off, dark_off))
                if max_off > 0:
                    folder_datetime = datetime.strptime(working_dir.replace(cst.base_path, '').split(os.sep)[1], '%y%m%d')

                    new_line = np.array([folder_datetime.date(), "Flat file", binning, fltr, bias_off, dark_off, "-", 
                                         (folder_datetime + timedelta(days=max_off)).date(), savepath])
                    pd.append_pending_log(new_line)
                
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
        
#         # This block is not necessary yet, but it starts calculating time-based weights that can 
#         # be used to construct better master frames by interpolating multiple master biases

#         # Get the creation time relative to the start of the observation
#         cr_time_rel = cr_time - start_time
        
#         # Creation time scaled between 0 and 1:
#         # 0 means that it was created at the start;
#         # 0.5 exactly halfway through the night;
#         # 1 at the end of the night.
#         cr_time_scl = cr_time_rel / time_diff
        
        # Retrieve the closest master correction frames
        try:
            master_bias, mbias_path, bias_off = get_closest_master(creation_datetime, working_dir, binning, "master_bias")
            master_dark, mdark_path, dark_off = get_closest_master(creation_datetime, working_dir, binning, "master_dark")
            master_flat, mflat_path, flat_off = get_closest_master(creation_datetime, working_dir, binning, "master_flat", fltr=fltr)
        except ers.SuitableMasterMissingError as err:
            warnings.warn(f"Reduction failed: {err} for {light_file}")
            # Let's hope the pending log can someday fix this 
            folder_datetime = datetime.strptime(working_dir.replace(cst.base_path, '').split(os.sep)[1], '%y%m%d')
            new_line = np.array([folder_datetime.date(), "Light file", binning, fltr, "?", "?", "?", "-", light_file])
            pd.append_pending_log(new_line)
            continue
            
        # Open the content of the current light fits
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
        
        # Add to the pending log if need be
        max_off = abs(max(bias_off, dark_off, flat_off))
        if max_off > 0:
            folder_datetime = datetime.strptime(working_dir.replace(cst.base_path, '').split(os.sep)[1], '%y%m%d')
            new_line = np.array([folder_datetime.date(), "Light file", binning, fltr, bias_off, dark_off, flat_off, 
                                 (folder_datetime + timedelta(days=max_off)).date(), light_file])
            pd.append_pending_log(new_line)
            
def reduce_img(obs, working_dir, args, light_file, max_days_off):
    """ Function that closely resembles reduce_imgs(), but this
        version is only reduced to reduce a specific light file. 
        Its main usage is in the pending mechanism
    """
    # Retrieve basic information
    binning, fltr, exptime, crtn = obs.get_file_info(light_file, ["BINNING", "FILTER", "EXPTIME", "DATE-OBS"])
    creation_datetime = datetime.strptime(crtn, "%Y-%m-%dT%H:%M:%S.%f")

    # Retrieve the closest master correction frames
    try:
        master_bias, mbias_path, bias_off = get_closest_master(creation_datetime, working_dir, binning,
                                                               "master_bias", max_days_off=max_days_off)
        master_dark, mdark_path, dark_off = get_closest_master(creation_datetime, working_dir, binning,
                                                               "master_dark", max_days_off=max_days_off)
        master_flat, mflat_path, flat_off = get_closest_master(creation_datetime, working_dir, binning,
                                                               "master_flat", fltr=fltr, max_days_off=max_days_off)
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

    # Add to the pending log if need be
    max_off = abs(max(bias_off, dark_off, flat_off))
    if max_off > 0:
        folder_datetime = datetime.strptime(working_dir.replace(cst.base_path, '').split(os.sep)[1], '%y%m%d')
        new_line = np.array([folder_datetime.date(), "Light file", binning, fltr, bias_off, dark_off, flat_off, 
                             (folder_datetime + timedelta(days=max_off)).date(), light_file])
        pd.append_pending_log(new_line)
        
def recreate_mdark(obs, working_dir, args, file_path, binning, fltr):
    # Re-initialise basic information
    cor_dir, filename = os.path.split(file_path)
    filename = filename.split(".")[0]
    cluster = filename.replace("master_dark", "").replace(binning, "")
    cluster = int(cluster.replace("C", "")) - 1
        
    # Get the master dark for this cluster and save it
    all_mdark, dark_clusters, used_mbias, biases_off = get_master_dark(obs, binning, working_dir,
                                                                cluster=cluster)
    
    # Get the master bias and cluster files
    mdark = all_mdark[0]
    dark_cluster = dark_clusters[0]
    mbias_path = used_mbias[0]
    bias_off = biases_off[0]

    # Master dark creation failed.
    if mdark.size == 0:
        return

    # Add origin files to the header
    header = fits.getheader(dark_cluster[-1])
    header = header_add_origin(header, dark_cluster)
    header = header_add_mbias(header, mbias_path, days_off=bias_off)

    # Overwrite the old master dark and the updated header
    filename = "master_dark" + binning + "C" + str(cluster+1) + ".fits"
    savepath = os.path.join(cor_dir, filename)
    save_fits(mdark, header, savepath)
    ut.Print(f"{savepath} created", args)

    # Add to the pending log if need be
    max_off = abs(bias_off)
    if max_off > 0:
        folder_datetime = datetime.strptime(working_dir.replace(cst.base_path, '').split(os.sep)[1], '%y%m%d')
        new_line = np.array([folder_datetime.date(), "Dark file", binning, fltr, bias_off, "-", "-",
                             (folder_datetime + timedelta(days=max_off)).date(), savepath])
        pd.append_pending_log(new_line)
                
def recreate_mflat(obs, working_dir, args, file_path, binning, fltr):
    # Re-initialise basic information
    cor_dir, filename = os.path.split(file_path)
    filename = filename.split(".")[0]
    cluster = filename.replace("master_dark", "").replace(binning, "").replace(fltr, "")
    cluster = int(cluster.replace("C", "")) - 1
    
    # Get the master flat for this cluster and save it
    all_mflat, flat_clusters, mbias_paths, mdark_paths, biases_off, darks_off = get_master_flat(obs, binning, fltr, 
                                                                                                working_dir, cluster=cluster)
    # Get the master bias, dark and cluster files
    mflat = all_mflat[0]
    flat_cluster = flat_clusters[0]
    mbias_path = mbias_paths[0]
    mdark_path = mdark_paths[0]
    bias_off = biases_off[0]
    dark_off = darks_off[0]

    # Master flat creation failed.
    if mflat.size == 0:
        return

    # Add origin files to the header
    header = fits.getheader(flat_cluster[-1])
    header = header_add_origin(header, flat_cluster)
    header = header_add_mbias(header, mbias_path, days_off=bias_off)
    header = header_add_mdark(header, mdark_path, days_off=dark_off)

    # Overwrite the old master flat and the updated header
    filename = "master_flat" + binning + fltr + "C" + str(cluster+1) + ".fits"
    savepath = os.path.join(cor_dir, filename)
    save_fits(mflat, header, savepath)
    ut.Print(f"{savepath} created", args)

    # Add to the pending log if need be
    max_off = abs(max(bias_off, dark_off))
    if max_off > 0:
        folder_datetime = datetime.strptime(working_dir.replace(cst.base_path, '').split(os.sep)[1], '%y%m%d')

        new_line = np.array([folder_datetime.date(), "Flat file", binning, fltr, bias_off, dark_off, "-", 
                             (folder_datetime + timedelta(days=max_off)).date(), savepath])
        pd.append_pending_log(new_line)
    
def header_add_origin(header, files):
    header.set(cst.HKW_nsource, str(len(files)))
    for filepath in files:
        ind = files.index(filepath)
        header.set(cst.HKW_source + str(ind+1), str(filepath))
    return header

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