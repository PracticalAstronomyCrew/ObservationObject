from astropy.io import fits
from datetime import datetime, timedelta
import numpy as np
import os
import warnings

import core.constants as cst
import core.errors as ers
import core.pending as pd
from core.pluginsystem import Plugin
import core.printstatus as ps

import logging
logger = logging.getLogger(__name__)
from blaauwpipe import BlaauwPipe

class Correction(Plugin):
    def __init__(self):
        super().__init__()
        self.title = "The Correction-Creator"
        self.call_level = 200
        self.command = "c"
        self.command_full = "correction"
        self.description = """ Core plugin that generated the master correction frames from the cst.raw_dir
                               and stores them in cst.cor_dir. Loops over every possible binning (and filter 
                               if applicable) and creaed the master files for each cluster of frames.
                           """

    def on_run(self, obs, plp):
        self.create_corrections(obs, plp)
        
    def create_corrections(self, obs, plp):
        """ Function that generates and saves all possible master correction 
            frames, for each cluster, binning and filter. Keep in mind that a
            cluster is a group of files that belong together, when consecutive
            frames are taken less than 60min apart from each other.
        """
        
        # Initiliase or create the saving dir for raw frames
        if not os.path.isdir(plp.cor_dir): os.mkdir(plp.cor_dir)
            
        ps.done(f"Savepath created at {BlaauwPipe.strip_filepath(plp.cor_dir)}")

        # Get the unique binnings/filters for this observation
        binnings = obs.get_binnings(plp.lightFiles)
        fltrs = obs.get_filters(plp.flatFiles)

        # Loop over every possible binning
        for binning in binnings:
            # Handle the master bias
            b_clusters = plp.get_bias_clusters(binning)
            for b_cluster in b_clusters:
                self.create_mbias(obs, plp, b_cluster, b_clusters.index(b_cluster))

            # Handle the master dark
            d_clusters = plp.get_dark_clusters(binning)
            for d_cluster in d_clusters:
                self.create_mdark(obs, plp, d_cluster, d_clusters.index(d_cluster))

            # Handle the master flats
            # First, loop over every filter
            for fltr in fltrs:
                f_clusters = plp.get_flat_clusters(binning, fltr)
                for f_cluster in f_clusters:
                    self.create_mflat(obs, plp, f_cluster, fltr, f_clusters.index(f_cluster))
        
        ps.done(f"Added source files keywords to headers")
        ps.done(f"Successfully created master correction frames!")
    
    @staticmethod
    def create_mbias(obs, plp, b_cluster, index):
        """ Function that creates the master bias for a specified b_cluster for 
            the passed Observation Object. This function wraps the Observation
            Object's create_master_bias method, to construct a master bias which 
            corresponds to the passed cluster. The newly generated master bias 
            is directly saved within this function. Note that also a header is 
            added to the master bias, which is a direct copy of the header from 
            the final frame of this bias cluster.
        """
        # Get additional info
        binning, fltr = plp.get_file_info(b_cluster[-1], ["BINNING", "FILTER"])
        
        ps.running(f"Creating {binning} Master bias for cluster {index+1}")

        # Generate the master bias
        mbias = plp.create_master_bias(b_cluster)

        # Add source files to the header
        header = fits.getheader(b_cluster[-1])
        header = BlaauwPipe.header_add_source(header, b_cluster)

        # Save the master bias and the updated header
        filename = "master_bias" + binning + "C" + str(index+1) + ".fits"
        savepath = os.path.join(plp.cor_dir, filename)
        BlaauwPipe.save_fits(savepath, data=mbias, header=header)
            
        ps.updateDone(f"{binning} Master bias saved at {BlaauwPipe.strip_filepath(savepath)}")
    
    @staticmethod
    def create_mdark(obs, plp, d_cluster, index, max_days_off=365):
        """ Function that creates the master bias for a specified d_cluster for 
            the passed Observation Object. This function wraps the Observation
            Object's create_master_dark method, to construct a master dark which 
            corresponds to the passed cluster. The newly generated master dark 
            is directly saved within this function. Note that also a header is 
            added to the master dark, which is a direct copy of the header from 
            the final frame of this bias cluster. The master bias file used for
            reduction is the closest bias frame that can be found, up to 
            max_days_off days from the current plp.working_dir.
        """
        # Get additional info
        binning, fltr = plp.get_file_info(d_cluster[-1], ["BINNING", "FILTER"])
        
        ps.running(f"Creating {binning} Master dark for cluster {index+1}")

        # Find the closest master bias to the dark creation time
        dark_creation = datetime.strptime(fits.getval(d_cluster[-1], 'DATE-OBS'), "%Y-%m-%dT%H:%M:%S.%f")
        try:
            closest_mbias, mbias_path, bias_off = BlaauwPipe.get_closest_master(dark_creation, plp,
                                                                       max_days_off, binning, "master_bias")
            logging.info(f"Closest master bias (days_off={bias_off}) of size closest_mbias.shape: {mbias_path}")
        except ers.SuitableMasterMissingError as err:
            warnings.warn(f"Master dark creation failed: {err} for {plp.working_dir}")
            logging.warn(f"SuitableMasterMissingError: could not find frames for dark cluster {index+1}")

            # Let's hope the pending log can someday fix this 
            new_line = np.array([dark_creation.date(), "Dark file", binning, fltr, "?", "-", "-", "-", d_cluster[0]])
            pd.append_pending_log(new_line)
            return

        # Generate the master dark using the found master bias
        mdark = plp.create_master_dark(d_cluster, closest_mbias)

        # Add source files to the header
        header = fits.getheader(d_cluster[-1])
        header = BlaauwPipe.header_add_source(header, d_cluster)
        header = BlaauwPipe.header_add_mbias(header, mbias_path, days_off=bias_off)

        # Save the master dark and the updated header
        filename = "master_dark" + binning + "C" + str(index+1) + ".fits"
        savepath = os.path.join(plp.cor_dir, filename)
        BlaauwPipe.save_fits(savepath, data=mdark, header=header)
        
        ps.updateDone(f"{binning} Master dark saved at {BlaauwPipe.strip_filepath(savepath)}")

        # Add to the pending log if need be
        max_off = abs(bias_off)
        if max_off > 0:
            folder_datetime = datetime.strptime(plp.working_dir.replace(cst.base_path, '').split(os.sep)[1], '%y%m%d')
            new_line = np.array([folder_datetime.date(), "Dark file", binning, fltr, bias_off, "-", "-",
                                 (folder_datetime + timedelta(days=max_off)).date(), savepath])
            pd.append_pending_log(new_line)
    
    @staticmethod
    def create_mflat(obs, plp, f_cluster, fltr, index, max_days_off=365):
        """ Function that creates the master bias for a specified d_cluster for 
            the passed Observation Object. This function wraps the Observation
            Object's create_master_dark method, to construct a master dark which 
            corresponds to the passed cluster. The newly generated master dark 
            is directly saved within this function. Note that also a header is 
            added to the master dark, which is a direct copy of the header from 
            the final frame of this bias cluster. The master bias and dark files
            used for reduction are the closest frame that can be found, up to 
            max_days_off days from the current plp.working_dir.
        """
        # Get additional info
        binning, fltr = plp.get_file_info(f_cluster[-1], ["BINNING", "FILTER"])
        
        ps.running(f"Creating {binning} Master flat of filter {fltr} for cluster {index+1}")

        # Find the closest master bias and master dark to the flat creation time
        flat_creation = datetime.strptime(fits.getval(f_cluster[-1], 'DATE-OBS'), "%Y-%m-%dT%H:%M:%S.%f")
        try:
            closest_mbias, mbias_path, bias_off = BlaauwPipe.get_closest_master(flat_creation, plp, max_days_off,
                                                                            binning, "master_bias")
            logging.info(f"Closest master bias (days_off={bias_off}) of size closest_mbias.shape: {mbias_path}")
            closest_mdark, mdark_path, dark_off = BlaauwPipe.get_closest_master(flat_creation, plp, max_days_off,
                                                                            binning, "master_dark")
            logging.info(f"Closest master dark (days_off={dark_off}) of size closest_mdark.shape: {mdark_path}")
            
        except ers.SuitableMasterMissingError as err:
            warnings.warn(f"Master flat creation failed: {err} for {plp.working_dir}")
            logging.warn(f"SuitableMasterMissingError: could not find frames for flat cluster {index+1} of filter {fltr}")

            # Let's hope the pending log can someday fix this 
            new_line = np.array([flat_creation.date(), "Flat file", binning, fltr, "?", "?", "-", "-", f_cluster[0]])
            pd.append_pending_log(new_line)
            return

        # Generate the master flat using the found master bias and master dark
        mflat = plp.create_master_flats(f_cluster, [fltr], closest_mbias, closest_mdark)
        # Add source files to the header
        header = fits.getheader(f_cluster[-1])
        header = BlaauwPipe.header_add_source(header, f_cluster)
        header = BlaauwPipe.header_add_mbias(header, mbias_path, days_off=bias_off)
        header = BlaauwPipe.header_add_mdark(header, mdark_path, days_off=dark_off)

        # Save the master flat and the updated header
        filename = "master_flat" + binning + fltr + "C" + str(index+1) + ".fits"
        savepath = os.path.join(plp.cor_dir, filename)
        BlaauwPipe.save_fits(savepath, data=mflat, header=header)
        
        ps.updateDone(f"{binning} Master flat of filter {fltr} saved at {BlaauwPipe.strip_filepath(savepath)}")

        # Add to the pending log if need be
        max_off = abs(max(bias_off, dark_off))
        if max_off > 0:
            folder_datetime = datetime.strptime(plp.working_dir.replace(cst.base_path, '').split(os.sep)[1], '%y%m%d')
            new_line = np.array([folder_datetime.date(), "Flat file", binning, fltr, bias_off, dark_off, "-", 
                                 (folder_datetime + timedelta(days=max_off)).date(), savepath])
            pd.append_pending_log(new_line)
    
    @staticmethod
    def recreate_mdark(obs, plp, file_path, binning, fltr):
        """ Function that recreates the environment needed to re-reduce the 
            dark file located at file_path. Used only in the pending mechanism.
        """
        # Re-initialise basic information
        cor_dir, filename = os.path.split(file_path)
        filename = filename.split(".")[0]
        cluster = filename.replace("master_dark", "").replace(binning, "")
        cluster_index = int(cluster.replace("C", "")) - 1

        # Handle the master dark
        d_clusters = plp.get_dark_clusters(binning)
        create_mdark(obs, plp.working_dir, args, d_clusters[cluster_index], cluster_index)
    
    @staticmethod
    def recreate_mflat(obs, plp, file_path, binning, fltr):
        """ Function that recreates the environment needed to re-reduce the 
            flat file located at file_path. Used only in the pending mechanism.
        """
        # Re-initialise basic information
        cor_dir, filename = os.path.split(file_path)
        filename = filename.split(".")[0]
        cluster = filename.replace("master_dark", "").replace(binning, "").replace(fltr, "")
        cluster_index = int(cluster.replace("C", "")) - 1

        f_clusters = plp.get_flat_clusters(binning, fltr)
        create_mflat(obs, plp.working_dir, args, f_clusters[cluster_index], fltr, cluster_index)
        