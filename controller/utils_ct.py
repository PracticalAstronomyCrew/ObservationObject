from datetime import datetime
import os
import constants_ct as cst

def Print(message, args, forced=False):
    now = datetime.now().time()
    if forced:
        print(now, message)
    elif args.verbose: 
        print(now, message)
        
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
        print("Foldertype not understood")
                
    return targets

def get_targets_from_date(date_text):
    date_stripped = date_text.replace("-", "")
    folder = os.path.join(cst.tele_path, date_stripped)
    
    targets = get_targets_from_folder(folder)
    return targets