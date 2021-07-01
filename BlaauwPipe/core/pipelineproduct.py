import core.constants as cst
from core.observation import Observation

from astropy.io import fits
from os import listdir
from os.path import isfile, join, getmtime, exists

class PipelineProduct(Observation):
    
    def __init__(self, foldername):
        self.working_dir = self.foldername = foldername
        self.raw_dir = join(self.working_dir, cst.raw_dir)
        self.cor_dir = join(self.working_dir, cst.correction_dir)
        self.red_dir = join(self.working_dir, cst.reduced_dir)
        
        super().__init__(foldername)
        self.group_correction_content()
        self.group_reduced_content()
        self.get_logfile()
        
        self.raw_files = self.files
        self.cor_files = self.masterFrames
        self.red_files = self.redLightFiles

    def group_raw_content(self):
        """
        Private method that loops over all the files in the given foldername, and groups them into 
        their respective list based on their image type. Besides, it keeps track of all the 
        different filters it comes across.
        """
        if not exists(self.raw_dir): return
            
        # These keywords are needed for categorising
        keywords = ["IMAGETYP", "EXPTIME", "FILTER"]
        
        # Lists containing the designated files. In the end, these become object attributes
        lightFiles = []
        biasFiles = []
        darkFiles = []
        flatFiles = []       
        
        # Get the (valid!) files in the given folder, so either .fits or .fit
        folderContent = [join(self.raw_dir, file) for file in listdir(self.raw_dir)
                         if (isfile(join(self.raw_dir, file)) and (file.endswith(".fits") or file.endswith(".FIT")))]

        # Sort the content on modification date
        sortedContent = sorted(folderContent, key=getmtime)
        
        # Loop over each file in the data dir       
        for filename in sortedContent: 
            imgtype, exptime, fltr = super().get_file_info(filename, keywords)

            # The following block orders the datafiles into the specified lists
            if "Bias" in imgtype: biasFiles.append(filename)
            elif "Dark" in imgtype: darkFiles.append(filename)
            elif "Flat" in imgtype: flatFiles.append(filename)
            elif "Light" in imgtype: lightFiles.append(filename)
                
        filterTypes = super().get_filters(sortedContent)
        binningTypes = super().get_binnings(sortedContent)
        
        # Turn every list that we have into an object attribute
        self.files = sortedContent
        self.lightFiles = lightFiles
        self.biasFiles = biasFiles
        self.darkFiles = darkFiles
        self.flatFiles = flatFiles
        self.filters = filterTypes
        self.binnings = binningTypes
        
    def group_correction_content(self):
        if not exists(self.cor_dir): return
        
        # These keywords are needed for categorising
        keywords = ["IMAGETYP", "EXPTIME", "FILTER"]
        
        # Lists containing the designated files. In the end, these become object attributes
        masterBiases = []
        masterDarks = []
        masterFlats = []       
        
        # Get the (valid!) files in the given folder, so either .fits or .fit
        folderContent = [join(self.cor_dir, file) for file in listdir(self.cor_dir)
                         if (isfile(join(self.cor_dir, file)) and (file.endswith(".fits") or file.endswith(".FIT")))]

        # Sort the content on modification date
        sortedContent = sorted(folderContent, key=getmtime)
        
        # Loop over each file in the data dir       
        for filename in sortedContent: 
            imgtype, exptime, fltr = super().get_file_info(filename, keywords)

            # The following block orders the datafiles into the specified lists
            if "Bias" in imgtype: masterBiases.append(filename)
            elif "Dark" in imgtype: masterDarks.append(filename)
            elif "Flat" in imgtype: masterFlats.append(filename)
                
        filterTypes = super().get_filters(sortedContent)
        binningTypes = super().get_binnings(sortedContent)
        
        self.masterFrames = sortedContent
        self.masterBiases = masterBiases
        self.masterDarks = masterDarks
        self.masterFlats = masterFlats   
        self.masterFilterTypes = filterTypes
        self.masterBinningTypes = binningTypes
        
    def group_reduced_content(self):
        if not exists(self.red_dir): return
        
        # These keywords are needed for categorising
        keywords = ["IMAGETYP", "EXPTIME", "FILTER"]
        
        # Get the (valid!) files in the given folder, so either .fits or .fit
        folderContent = [join(self.red_dir, file) for file in listdir(self.red_dir)
                         if (isfile(join(self.red_dir, file)) and (file.endswith(".fits") or file.endswith(".FIT")))]

        # Sort the content on modification date
        sortedContent = sorted(folderContent, key=getmtime)
                
        filterTypes = super().get_filters(sortedContent)
        binningTypes = super().get_binnings(sortedContent)
        
        self.redLightFiles = sortedContent
        self.redFilterTypes = filterTypes
        self.redBinningTypes = binningTypes
        
    def get_logfile(self):
        self.logfile = ""
        logpath = join(self.working_dir, cst.logfile)
        if exists(logpath) and isfile(logpath):
            self.logfile = logpath