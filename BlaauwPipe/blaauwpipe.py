import core.constants as cst
import core.errors as ers
from core.observation import Observation
from core.pipelineproduct import PipelineProduct
import core.printstatus as ps
from core.pluginsystem import PluginCollector

import argparse
from astropy.io import fits
from datetime import datetime, timedelta
import logging
import numpy as np
import os
import sys
import time
import warnings

#--------------------DEBUG-ONLY---------------------#
from importlib import reload
mods = [cst]
for mod in mods:
    reload(mod)
#---------------------------------------------------#

class BlaauwPipe(object):
    
    def __init__(self):
        self.print_logo()
        
        # Retrieve the arguments, and the specified targets
        self.load_args()
        
    def print_logo(self):
        print(cst.logo)
        print(cst.cr)
        print("")

    def start(self):
        # Loop over every target that was found and perform the actions 
        # that were specified in the command line arguments
        for self.target in self.targets:
            ps.module("Booting BlaauwPipe")
            ps.done(f"Current target: {self.target}")

            # Construct a working dir where all *new/altered* data goes
            working_dir_name = os.path.relpath(self.target, cst.tele_path)
            self.working_dir = os.path.join(cst.base_path, working_dir_name)

            # Extra check if the working dir already exists, else create it
            if os.path.isdir(self.working_dir):
                # TODO: this means this data probably has been handled already...
                # BUT: not sure what exact operations have been carried out
                # Maybe we can put some sort of log in each handled dir, containing
                # a list of all actions that were already performed? Seems better 
                # than just 'checking' manually what has or hasn't been done yet.
                #print("Folder existed")
                pass
            else:
                os.makedirs(self.working_dir)
                
            # Initialize log file
            logfile_path = os.path.join(self.working_dir, cst.logfile)
            logging.basicConfig(filename=logfile_path, 
                                level=logging.DEBUG, 
                                force=True, 
                                format='%(asctime)s %(levelname)s %(module)s - %(funcName)s: %(message)s',
                                datefmt='%Y-%m-%d %H:%M:%S.%03d')
            logging.info("Blaauwpipe: " + cst.cr)
            ps.done(f"Logfile created at {BlaauwPipe.strip_filepath(logfile_path)}")
            
            # Create observation object for this target
            self.create_observation()
            self.create_pipelineproduct()
            
            ps.module("BlaauwPipe booted succesfully!")
            ps.newline()

            # Perform core functions
            self.get_plugins()
            self.run_plugins()
            
        if not self.targets:
            ps.module("Booting BlaauwPipe")
            ps.failed("No observation directories found for specified target!", log=False)
            ps.module("Booting BlaauwPipe failed")
        
        else:
            print("BlaauwPipe done!")
            
        print("")
                
    def load_args(self):
        """ Function that specifies the expected arguments
            given on the command line by the user.
        """

        # Sets the description that will be shown with --help
        parser = argparse.ArgumentParser(description="Program that updates the Blaauw Observatory \
                                                      database by automatically reducing the fits files")

        # Add required argument for path to observation folder
        target = parser.add_mutually_exclusive_group()
        target.add_argument("-f", "--folder", type=str, help="The absolute path to the observation directory")
        target.add_argument("-d", "--date", type=str, help="The observation date in yy-mm-dd")
        target.add_argument("-u", "--update", action='store_const', const=datetime.today().strftime("%y-%m-%d"),
                            dest="date", help="Select todays directory if it exists")

        # Add arguments for the intended action
        parser.add_argument("-b", "--backup", action="store_true", help="Move a copy of the raw data to local folder")
        parser.add_argument("-c", "--correction", action="store_true", help="Save raw correction frames locally")
        parser.add_argument("-r", "--reduce", action="store_true", help="Reduce all the present light frames")
        #parser.add_argument("-p", "--preview", action="store_true", help="Create a .png preview per light file")
        parser.add_argument("-p", "--pending", action="store_true", help="Rerun pending reductions")
        parser.add_argument("-a", "--astrometry", action="store_true", help="Run raw&reduced light files through Astrometry")
        parser.add_argument("-m", "--modules", action="store_true", help="Run external modules stored in /plugins")

        # Retrieve the passed arguments and check their validity
        self.args = parser.parse_args()
        self.parser = parser
        self.targets = self.check_args()
        
    def check_args(self):
        """ Function that checks all the given arguments for their validity. If one
            of the required conditions is not met, an error is thrown.
        """
        parser=self.parser; args=self.args
        # Check that a target was specified
        if not (args.folder or args.date):
            parser.error(f"Target was not specified: pass a directory path or a date")

        # If the target is a directory, get the datasets it contains
        if args.folder:
            if not os.path.isdir(args.folder):
                parser.error(f"{args.folder} is not an existing directory")
            targets = BlaauwPipe.get_targets_from_folder(folder)

        # If the target is a date, get the datasets this date contains
        elif args.date:
            if not self.is_valid_date(args.date, "%y-%m-%d"):
                parser.error(f"{args.date} is not a valid date. Use the following format: yy-mm-dd")
            targets = BlaauwPipe.get_targets_from_date(args.date)

        # The action was not specified
        if not (args.backup or args.correction or args.reduce or 
                args.pending or args.astrometry or args.modules):
            parser.error("No action specified. Possible actions include: --backup, --reduce, --pending and --modules")

        # Update the user on the found contents
    #     if len(targets) > 0:
    #         Print(f"Found data in {len(targets)} subdir(s)", args, True)
    #     else:
    #         Print("No data found for this target", args, True)
            # sys.exit() met script

        return targets
    
    def check_obs(self):
        """ Function that checks some properties of the generated 
            Observation object. Nothing fancy, just some extra checks 
            to prevent unforeseen circumstances...
        """
        obs=self.obs; args=self.args
        
        # Update the user on the found content
        ps.updateDone(f"Found {len(obs.files)} fits files")
        ps.done(f"  {len(obs.lightFiles)} light frames")

        # Now, check what correction frame types we have
        frame_check = 3

        # Check for the presence of bias frames
        bias_found = len(obs.biasFiles) > 0
        if not bias_found:
            ps.warning("No bias files were found")
            frame_check -= 1
        else: ps.done(f"  {len(obs.biasFiles)} bias frames")

        # Check for dark presence of frames    
        dark_found = len(obs.darkFiles) > 0
        if not dark_found:
            ps.warning("No dark files were found")
            frame_check -= 1
        else: ps.done(f"  {len(obs.darkFiles)} dark frames")
            
        # Check for flat presence of fields
        flat_found = len(obs.flatFiles) > 0
        if not flat_found:
            ps.warning("No flat fields were found")
            frame_check -= 1
        else: ps.done(f"  {len(obs.flatFiles)} flat fields")

        # Not likely to happen, but raise an error if
        # literally no correction frames were found
        if frame_check == 0:
            raise ers.MissingFramesError("No suitable correction frames found")

        return
    
    def create_observation(self):
        """ Function that creates the observation object for the 
            passed target. Also performs some small checkups to 
            be sure that we have some proper data.
        """
        target=self.target; args=self.args
        ps.running(f"Looking for files in {self.target}")
        self.obs = Observation(target)  
        self.check_obs()
        ps.done("Observation Object initialized")
        
    def create_pipelineproduct(self):
        ps.running("Initializing Pipeline Product...")
        self.plp = PipelineProduct(self.working_dir)
        ps.updateDone("Pipeline Product initialized")
        
    #-----------------------------------------#
    #            Validity checkers            #
    #-----------------------------------------#
    
    @staticmethod
    def is_valid_date(date_text, date_format):
        try:
            datetime.strptime(date_text, date_format)
            return True
        except ValueError:
            return False
    
    @staticmethod
    def get_targets_from_folder(folder):
        """ Function that extracts the actual telescope folders from the passed 
            folder. There exist two options: the given folder is either a specific 
            dataset, or a parent directory for a specific date. In either case, a 
            list is returned containing all the valid date subfolders.
        """
        folder = os.path.normpath(folder)

        # In this case, the passed folder is specific
        if folder.endswith(cst.tele_subsubdirs):
            targets = [folder]

        elif folder.endswith(cst.tele_subdirs):
            subdirs = [os.path.join(folder, subdir) for subdir in cst.tele_subsubdirs]
            targets = []
            for subdir in subdirs:
                if len(os.listdir(subdir)) > 0:
                    targets.append(subdir)

        elif BlaauwPipe.is_valid_date(os.path.basename(os.path.normpath(folder)), "%y%m%d"):
            subdirs = [os.path.join(folder, subdir) for subdir in cst.tele_subdirs]
            targets = []
            for subdir in subdirs:
                for subsubdir in cst.tele_subsubdirs:
                    cur_folder = os.path.join(subdir, subsubdir)
                    if os.path.isdir(cur_folder) and len(os.listdir(cur_folder)) > 0:
                        targets.append(cur_folder)

        else:
            Print("Foldertype not understood", args)

        return targets

    @staticmethod
    def get_targets_from_date(date_text):
        date_stripped = date_text.replace("-", "")
        folder = os.path.join(cst.tele_path, date_stripped)
        targets = BlaauwPipe.get_targets_from_folder(folder)
        return targets
    
    @staticmethod
    def strip_filepath(path, strip=cst.base_path):
        stripped = path.replace(strip, "")
        stripped_path = f"~{stripped}"
        return stripped_path
    
    
    #-----------------------------------------#
    #              Plugin runner              #
    #-----------------------------------------#
        
    def get_plugins(self):
        # Backup - Correction - Reduce - Astrometry - External
        # Collect all core plugins
        self.core_plugins = PluginCollector("core").plugins
        
        # Collect all external plugins
        self.extra_plugins = PluginCollector("plugins").plugins
        
        # Select only the enabled plugins and save them to self.plugins
        arg_plugins = [k for k, v in vars(self.args).items() if v == True]
        self.plugins = [plugin for plugin in self.core_plugins if plugin.command_full in arg_plugins]
        if self.args.modules:
            [self.plugins.append(plugin) for plugin in self.extra_plugins]
            
        # Order self.plugins based on the call levels of the plugins
        self.plugins.sort(key=lambda plugin: plugin.call_level)
        
        
    def run_plugins(self):
        # Execute each plugin
        for plugin in self.plugins:
            ps.module(f"Running {'core' if 'core' in plugin.__module__ else 'external'} plugin: {plugin.title}")
            plugin.on_run(self.obs, self.plp)
            ps.module(f"Plugin {plugin.title} executed!")
            ps.newline()

    def run_plugins_single(self, obs, plp, args, file, called_from):
        # Collect all plugins
        loaded_plugins = PluginCollector()
        # Execute each plugin for a specific file only
        for plugin in loaded_plugins.plugins:
            # Only rerun plugin if specified by plugin
            # TODO: not really elegant to compare strings...
            if (called_from == "pending" and plugin.rerun_on_pending) or \
               (called_from == "astrometry" and plugin.rerun_on_astrometry):
                ut.Print(f"(Re)running external plugin: {plugin.title}", args)
                plugin.on_run_single(obs, plp, args, file)
                ut.Print(f"{plugin.title} (re-)executed", args)
                
                
    #-----------------------------------------#
    #               Misc. utils               #
    #-----------------------------------------#
    
    @staticmethod
    def get_closest_master(target_datetime, plp, max_days_off, binning, frame_type, fltr=""):
        """ Function that returns the closest file to target_datetime, given the
            requirements posed by binning, frametype and possibly fltr. Could for
            example be used to find the closest master Bias to a specific datetime.
            Tries to find potential files within the plp.working_dir first, but extends
            its search range to nearby dates when still no suitable files were found.
            Then, orders the potential files on creation time and returns the closest.
        """
        # Set the filename requirements
        requirements = [frame_type, binning, fltr]
        potential_files = []

        # First, look in the current workspace if there exist suitable files.
        # If yes, add them to a list, which will later be sorted on creation time.
        for filename in os.listdir(plp.cor_dir):
            # Requirements that filename should satisfy
            if not all(req in filename for req in requirements):
                continue
            # File satisfying the requirements found, so add its we add the filepath
            # and its creation time to the potentials list. The third argument, being
            # 0 here, represents the 'relative age' of this frame, see 'days_off'.
            file = os.path.join(plp.cor_dir, filename)
            creation_time = datetime.strptime(fits.getval(file, 'DATE-OBS'), "%Y-%m-%dT%H:%M:%S.%f")
            potential_files.append([file, creation_time, 0])

        # If we somehow still don't have any potential master files, we could look 
        # into directories of 'nearby' dates. We increase days_off by 1 each iteration
        # and check both the 'past' and the 'future' folders for suitable files
        folder_date = plp.working_dir.replace(cst.base_path, '').split(os.sep)[1]
        folder_datetime = datetime.strptime(folder_date, '%y%m%d')
        days_off = 1
        while len(potential_files) == 0:
            # Construct the 'future' datefolder corresponding to days_off
            next_cor_date = (folder_datetime + timedelta(days=days_off)).date().strftime('%y%m%d')
            next_cor_dir = plp.cor_dir.replace(folder_date, next_cor_date)

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
            prev_cor_dir = plp.cor_dir.replace(folder_date, prev_cor_date)

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

        # Return the data of the closest master, its path and its days_off.
        return closest_master, closest[0], closest[2]
    
    
    #-----------------------------------------#
    #               Fits utils                #
    #-----------------------------------------#

    @staticmethod
    def header_add_source(header, files):
        header.set(cst.HKW_nsource, str(len(files)))
        for filepath in files:
            ind = files.index(filepath)
            header.set(cst.HKW_source + str(ind+1), str(filepath))
        return header

    @staticmethod
    def header_add_traw(header, raw_file):
        header.set(cst.HKW_traw, raw_file)
        return header

    @staticmethod
    def header_add_praw(header, raw_file):
        header.set(cst.HKW_praw, raw_file)
        return header

    @staticmethod
    def header_add_pred(header, red_file):
        header.set(cst.HKW_pred, red_file)
        return header

    @staticmethod
    def header_add_mbias(header, mbias_path, days_off=None):
        header.set(cst.HKW_mbias, mbias_path)
        if days_off is not None:
            header.set(cst.HKW_mbias_age, days_off)
        return header

    @staticmethod
    def header_add_mdark(header, mdark_path, days_off=None):
        header.set(cst.HKW_mdark, mdark_path)
        if days_off is not None:
            header.set(cst.HKW_mdark_age, days_off)
        return header

    @staticmethod
    def header_add_mflat(header, mflat_path, days_off=None):
        header.set(cst.HKW_mflat, mflat_path)
        if days_off is not None:
            header.set(cst.HKW_mflat_age, days_off)
        return header

    @staticmethod
    def save_fits(save_path, data=None, header=None, overwrite=True):
        """ Takes the content of a fits file and saves it 
            as a new fits file at save_path
        """
        if os.path.exists(save_path) and data is None: data=fits.getdata(save_path)
        if os.path.exists(save_path) and header is None: header=fits.getheader(save_path)
        hduNew = fits.PrimaryHDU(data, header=header)
        hduNew.writeto(save_path, overwrite=overwrite)

    @staticmethod
    def get_kw(filepath, keyword):
        val = fits.getheader(filepath, 0)[keyword]
        return val
        
def main():
    bp = BlaauwPipe()
    bp.start()
    
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt as KI:
        import core.printstatus as ps
        ps.warning("KeyboardInterrupt! Exiting...")
        ps.newline()
        try:
            sys.exit(1)
        except SystemExit:
            os._exit(1)