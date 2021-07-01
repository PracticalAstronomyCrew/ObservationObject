from astropy.io import fits
from datetime import datetime
import os
from shutil import copy2
import stat

import core.constants as cst
from core.pluginsystem import Plugin
import core.printstatus as ps

import logging
logger = logging.getLogger(__name__)
from blaauwpipe import BlaauwPipe

class Backup(Plugin):
    def __init__(self):
        super().__init__()
        self.title = "The Backup-Maker"
        self.call_level = 100
        self.command = "b"
        self.command_full = "backup"
        self.description = """ Core plugin that copies all files in the original observation directory to
                               the external location at cst.raw_dir. Once the files are stored in this folder,
                               the header keyword TRAW will be appended which holds the path to the original
                               file. This plugin paves the way for the next actions, such as creating the 
                               master correction frames and reducing the light frames.
                           """

    def on_run(self, obs, plp):
        """ Copy all the files in the passed observation object
            to a new directory, just like a backup.
        """
        
        # Construct the save path
        if not os.path.isdir(plp.raw_dir): os.mkdir(plp.raw_dir)
            
        ps.done(f"Savepath created at {BlaauwPipe.strip_filepath(plp.raw_dir)}")

        # Make a copy of each file
        for ori_file in obs.files:
            filename = os.path.basename(ori_file)
            filepath = os.path.join(plp.raw_dir, filename)
            
            # Update user
            ps.progressBar(obs.files.index(ori_file), len(obs.files), f"Copying file to backup: {filename}")
            
            # Copy files
            copy2(ori_file, filepath)
            
            # Use chmod to ensure write permission (- rw- r-- r--)
            os.chmod(filepath, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH | stat.S_IWUSR)

            # Add header keyword TRAW
            header = fits.getheader(filepath)
            header = BlaauwPipe.header_add_traw(header, ori_file)
            BlaauwPipe.save_fits(filepath, header=header)
            
        ps.updateDone(f"Copying files done", progressbar=True)
        ps.done(f"Changed file permissions to rw-r--r--")
        ps.done(f"Added TRAW keyword to headers")
        ps.done(f"Successfully copied and prepared {len(obs.files)} files!")