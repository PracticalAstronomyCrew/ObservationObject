from datetime import datetime
import os
from shutil import copy2

import core.constants as cst
from core.observation import Observation

def Print(message, args, forced=False):
    now = datetime.now().time()
    if forced:
        print(now, message)
    elif args.verbose: 
        print(now, message)
        
def check_args(parser, args):
    """ Function that checks all the given arguments for their validity. If one
        of the required conditions is not met, an error is thrown.
    """
    # Check that a target was specified
    if not (args.folder or args.date):
        parser.error(f"Target was not specified: pass a directory path or a date")
    
    # If the target is a directory, get the datasets it contains
    if args.folder:
        if not os.path.isdir(args.folder):
            parser.error(f"{args.folder} is not an existing directory")
        targets = get_targets_from_folder(args.folder)
    
    # If the target is a date, get the datasets this date contains
    elif args.date:
        if not is_valid_date(args.date, "%y-%m-%d"):
            parser.error(f"{args.date} is not a valid date. Use the following format: yy-mm-dd")
        targets = get_targets_from_date(args.date)
    
    # The action was not specified
    if not (args.backup or args.correction or args.reduce or args.pending or args.modules):
        parser.error("No action specified. Possible actions include: --backup, --reduce, --pending and --modules")
        
    # Update the user on the found contents
    if len(targets) > 0:
        Print(f"Found data in {len(targets)} subdir(s)", args, True)
    else:
        Print("No data found for this target", args, True)
        # sys.exit() met script
        
    return targets

def is_valid_date(date_text, date_format):
    try:
        datetime.strptime(date_text, date_format)
        return True
    except ValueError:
        return False
    
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
        
    elif is_valid_date(os.path.basename(os.path.normpath(folder)), "%y%m%d"):
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

def get_targets_from_date(date_text):
    date_stripped = date_text.replace("-", "")
    folder = os.path.join(cst.tele_path, date_stripped)
    
    targets = get_targets_from_folder(folder)
    return targets
                
def check_obs(obs, args):
    """ Function that checks some properties of the generated 
        Observation object. Nothing fancy, just some extra checks 
        to prevent unforeseen circumstances...
    """
    # Update the user on the found content
    if args.verbose:
        Print(f"Found {len(obs.files)} fits files", args)
        Print(f"Found {len(obs.biasFiles)} bias frames", args)
        Print(f"Found {len(obs.darkFiles)} dark frames", args)
        Print(f"Found {len(obs.flatFiles)} flat fields", args)
        Print(f"Found {len(obs.lightFiles)} light frames", args)
    
    # For reducing, we also need the raw correction frames
#     if args.reduce:
#         args.correction = True
     
    # Now, check what correction frame types we have
    frame_check = 3
    
    # Check for the presence of bias frames
    bias_found = len(obs.biasFiles) > 0
    if not bias_found:
        warnings.warn("No bias files were found")
        frame_check -= 1
        
    # Check for dark presence of frames    
    dark_found = len(obs.darkFiles) > 0
    if not dark_found:
        warnings.warn("No dark files were found")
        frame_check -= 1
    
    # Check for flat presence of fields
    flat_found = len(obs.flatFiles) > 0
    if not flat_found:
        warnings.warn("No flat fields were found")
        frame_check -= 1
        
    # Not likely to happen, but raise an error if
    # literally no correction frames were found
    if frame_check == 0:
        raise ers.MissingFramesError("No suitable correction frames found")
    
    return

def get_observation(target, args):
    """ Function that creates the observation object for the 
        passed target. Also performs some small checkups to 
        be sure that we have some proper data.
    """
    Print("Creating Observation object...", args)
    obs = Observation(target)  
    check_obs(obs, args)
    Print("Observation object initialized", args, True)
    return obs