#!/usr/bin/env python
# coding: utf-8

# In[2]:


from astropy.io import fits
from datetime import datetime
import errno
import numpy as np
from os import listdir
from os.path import isfile, join, getmtime, exists
import warnings

class Observation:
    """
    This class provides a convenient way to access, view and manipulate the data of an observation
    night. An instance of this class is linked to a certain directory containing .fits or .fit files 
    generated by the telescope, which are read whenever needed. This object gives quick access to 
    bias, dark and flat field correction frames, each of which is customizable to the way you like it. 
    Light frames can be corrected using these or your own frames and can later be saved into your own 
    content folder. 
    
    Attributes:
        foldername:   path to data folder
        files:        list of all files present
        biasFiles:    list of all bias files
        darkFiles:    list of all dark files
        flatFiles:    list of all flat files
        masterBias:   2d ndarray representing master bias
        masterDark:   2d ndarray representing master dark
        masterFlats:  3d ndarray representing all master flats
        filters:      list of all filters found
        
    TODO:
        - Triple check that bias, dark and flat reduction is actually perfomed correctly
        - Evaluate efficiency of calculations and variable storing
        - Add methods that might be useful (Astrometry, saving, reducing images etc.)
        - And more probably
        
    Created by FGunnink on 02-10-2020
    Updated on 24-12-2020
    """
    
    def __init__(self, foldername):
        """
        Initialize an Observation object. One can either pass the data directory path or a file in 
        this same directory (for example: a .fits file). Raises an error whenever the system 
        cannot determine around which directory the Observation object should be created.
        
        Args:
            foldername (string): the (file- or) foldername the Observation object is built around.
            
        Raises:
            FileNotFoundError: the given folder could not be found.
            
        """
        
        # If a file was passed, rename variable to the folders parent dir
        if isfile(foldername):  
            fn = foldername.split("/")[-1]
            foldername = foldername.replace(fn, "")
        
        # Check whether the (passed or deduced) folder actually exists
        if not exists(foldername):
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), foldername)
            
        # Prime the newly created object with some attributes
        self.foldername = foldername
        self.masterBias = None
        self.masterDark = None
        self.masterFlats = None
        
        self.group_content(foldername)  # Group all the content of the folder
            
    def get_files(self, condit=None):
        """
        Public method that returns the files of this observation night that satisfy all the 
        keyword conditions given in condit. If this argument is left empty, it returns all the
        files available in this folder.
        
        Keyword Args:
            condit (dictionary): a dictionary with header conditions that the file should meet.
                                 The dictionary consists of header keywords as keys, and the wanted 
                                 requirements as the value. Note that values should sometimes be ints!
            
        Returns:
            result (list of strings): returns a list of strings that represent the absolute paths to 
                                      the files that satisfy all the conditions.
            
        """
        if condit is None:
            return self.files
        
        result = []
        keywords, values = zip(*condit.items())  # Unzip the dictionary in two lists
        
        for file in self.files:
            # If the total list of resulting values matches the requested values, add it to the results
            if self.get_file_info(file, keywords) == list(values):
                result.append(file)
            
        return result
        
    def group_content(self, foldername):
        """
        Private method that loops over all the files in the given foldername, and groups them into 
        their respective list based on their image type. Besides, it keeps track of all the 
        different filters it comes across.
        
        Args:
            foldername (string): an existing absolute path to the folder
        
        """
        # These keywords are needed for categorising
        keywords = ["IMAGETYP", "EXPTIME", "FILTER"]
        
        # Lists containing the designated files. In the end, these become object attributes
        lightFiles = []
        biasFiles = []
        darkFiles = []
        flatFiles = []
        filterTypes = []

        # Get the (valid!) files in the given folder, so either .fits or .fit
        folderContent = [join(foldername, file) for file in listdir(foldername)
                         if (isfile(join(foldername, file)
                            and (file.endswith(".fits")
                            or file.endswith(".FIT"))))]

        # Sort the content on modification date
        sortedContent = sorted(folderContent, key=getmtime)
        
        # Loop over each file in the data dir       
        for filename in sortedContent: 
            imgtype, exptime, fltr = self.get_file_info(filename, keywords)

            # The following block orders the datafiles into the specified lists
            if "Bias" in imgtype: biasFiles.append(filename)
            elif "Dark" in imgtype: darkFiles.append(filename)
            elif "Flat" in imgtype: flatFiles.append(filename)
            elif "Light" in imgtype: lightFiles.append(filename)

            # And store the different types of filters as well
            if fltr not in filterTypes: filterTypes.append(fltr)
        
        # Turn every list that we have into an object attribute
        self.files = sortedContent
        self.lightFiles = lightFiles
        self.biasFiles = biasFiles
        self.darkFiles = darkFiles
        self.flatFiles = flatFiles
        self.filters = filterTypes
        
    def get_file_info(self, filename, header_keywords):
        """
        Private method that reads a list of keywords, specified in header_keywords, in the header of
        the given file. Returns a list of the same size as header_keywords, with all the 
        resulting values. Introduces the (imaginary) "IMGSIZE" key, which is nothing more 
        than a fancy string representation of the NAXIS1 and NAXIS2 key.
        
        Args:
            filename (string): the absolute path to the file that needs to be looked into
            header_keywords (list of strings): the list of keywords you want to look for in the fits header
            
        Returns:
            results (list): returns a list of results, whose elements can be strings or integers

        """
        results = []

        # Open fits file and read the header from the first HDU object
        with fits.open(filename) as hduList:
            hdu = hduList[0]
            hduHeader = hdu.header

            # Loop over every keyword and read the correspoding value
            for keyword in header_keywords:
                try:
                    # Special custom keyword "IMGSIZE" (read method docstring)
                    if keyword == "IMGSIZE":
                        results.append(str(hduHeader["NAXIS1"]) + "x" + str(hduHeader["NAXIS2"]))
                    # Another special custom keyword "IMGSIZE" (read method docstring)
                    elif keyword == "BINNING":
                        results.append(str(hduHeader["XBINNING"]) + "x" + str(hduHeader["YBINNING"]))
                    else:
                        results.append(hduHeader[keyword])
                        
                # The keyword might not exist or be specified
                except:
                    results.append("?")

        return results
    
    def sort_closest(self, target, files):
        """
        Public method that sorts a list of passed files based on their creation time stored in the 
        fits header. This new list is sorted such that that the first element is closest to the 
        creation time of the target file. The next element is hence the next-closest, and so on.
        
        Args:
            target (string): the path to the target file whose time is read and compared to.
            files (list of strings): paths of the files that need to be compared to the target time
                                     and sorted accordingly.
                                     
        Returns:
            file_time_lst (list of 2D tuples): returns a list of 2D tuples, containing the path to 
                                               the file and their creation time.
        """
        
        # Read the creation time of the target file from the header
        target_time_str = self.get_file_info(target, ["DATE-OBS"])[0]
        target_time = datetime.strptime(target_time_str, '%Y-%m-%dT%H:%M:%S.%f')
        
        # List to store tuples of the passed files: (filepath, creation_time)
        file_time_lst = []
        
        # Loop over every passed file and get their creation time
        for file in files:
            filetime_str = self.get_file_info(file, ["DATE-OBS"])[0]
            filetime = datetime.strptime(filetime_str, '%Y-%m-%dT%H:%M:%S.%f')
            file_time_lst.append((file, filetime))
        
        # Sort this list on their difference with the target file
        file_time_lst = sorted(file_time_lst, key=lambda x: abs(x[1] - target_time))
        return file_time_lst
    
    def check_binning(self, files):
        """
        Public method that checks whether every passed file has the same binning.
        
        Args:
            files (list of strings): list of filepaths of the files that should be checked
            
        Returns:
            -
            
        Raises:
            IncompatibleBinningError
            
        """
        # First, assume every file is equally large
        binning = self.get_file_info(files[0], ["BINNING"])[0]
        
        # Then loop over every file and check their sizes
        for file in files:
            current_binning = self.get_file_info(file, ["BINNING"])[0]
            
            # If it differs from the first file, there's a problem
            if current_binning != binning:
                raise IncompatibleBinningError(file, binning, current_binning)
        
        return
        
    def create_master_bias(self, biasFiles=None):
        """
        Public method that creates the master bias matrix for all known bias files, or only for the
        list of files specified in the biasFiles argument. Returns the result and stores it in the
        self.masterBias attribute as well, to prevent having to construct it again.
        
        Keyword Args:
            biasFiles (list of strings): List of the absolute path to files from which the master bias
                                         should be constructed
            
        Returns:
            masterBias (numpy.ndarray): returns a matrix that represents the master bias
            
        """
        
        if biasFiles is None:
            biasFiles = self.biasFiles
            
        self.check_binning(biasFiles)
        
        stackedBiasData = None
        
        # Loop over each bias .fits file
        for i in range(len(biasFiles)):
            filename = biasFiles[i]

            # Open fits file and read the header from the first HDU object
            hduList = fits.open(filename)
            hdu = hduList[0]
            hduHeader = hdu.header

            # Get the width and length of the image
            NAXIS1 = hduHeader["NAXIS1"]
            NAXIS2 = hduHeader["NAXIS2"]
            
            # On the first loop, assign the hdu content to the variable
            if stackedBiasData is None:
                stackedBiasData = hdu.data 
            # Afterwards, the content of each file can be stacked on axis=2
            else:
                stackedBiasData = np.dstack((stackedBiasData, hdu.data))

        # One-dimensionalize the stacked data if needed
        if len(biasFiles) > 1:
            # Take the median of each row along axis=2
            masterBias = np.median(stackedBiasData, axis=2)
        else:
            masterBias = stackedBiasData

        # Store the master Bias for later reference
        self.masterBias = masterBias
        
        return masterBias
    
    def create_master_dark(self, darkFiles=None, masterBias=None):
        """
        Creates the master dark matrix for all known dark files (unless darkFiles argument is passed).
        If a masterBias matrix is provided, then this one will be used in the construction of the master
        dark. If not, it uses its own version. Returns the result and stores it in the self.masterDark
        attribute as well, to prevent having to construct it again.
        
        Keyword Args:
            darkFiles (list of strings): List of the absolute path to files from which the master dark
                                         should be constructed
            masterBias (numpy.ndarray): If specified, the master dark will be constructed using this
                                        master bias, instead of the default self.masterBias attribute
            
        Returns:
            masterDark (numpy.ndarray): returns a matrix that represents the master dark
            
        """
        
        if darkFiles is None:
            darkFiles = self.darkFiles
            
        self.check_binning(darkFiles)
            
        if masterBias is None:
            masterBias = self.masterBias
            
        # List to keep track of the exposure times of each dark frame
        EXPTIMEs = np.zeros(len(darkFiles))
        tolerance = 30  # Defines how large the biggest difference in exposure times should be

        stackedDarkData = None

        # Loop over each dark .fits file
        for i in range(len(darkFiles)):
            filename = darkFiles[i]

            # Open fits file and read the header from the first HDU object
            hduList = fits.open(filename)
            hdu = hduList[0]
            hduHeader = hdu.header

            # This block reads the EXPTIME keyword from the header and stores it in a list
            EXPTIME = hduHeader["EXPTIME"]
            EXPTIMEs[i] = EXPTIME
            
            # Get the width and length of the image
            NAXIS1 = hduHeader["NAXIS1"]
            NAXIS2 = hduHeader["NAXIS2"]
            
            # Subtract the masterBias frame
            darkBiasCorrected = hdu.data - masterBias 

            # On the first loop, assign the hdu content to the variable
            if stackedDarkData is None:
                stackedDarkData = darkBiasCorrected 
            # Afterwards, the content of each file can be stacked on axis=2
            else:
                stackedDarkData = np.dstack((stackedDarkData,darkBiasCorrected))

        # For the best results, all exposure times should more or less be the same, so check that
        avgEXPTIME = EXPTIMEs.mean()
        largestDiff = EXPTIMEs.max() - EXPTIMEs.min()
        
        # Warning the user about possible problems due to exposure times
        if largestDiff > tolerance:
            warnings.warn(f"The exposure time difference between dark frames is large: {largestDiff}s!")
            
        # One-dimensionalize the stacked data if needed
        if len(darkFiles) > 1:
            # Take the median of each row along axis=2
            masterDarkUnnorm = np.median(stackedDarkData, axis=2)
        else:
            masterDarkUnnorm = stackedDarkData

        # Normalize the frame by dividing by the average exposure time
        masterDark = masterDarkUnnorm / avgEXPTIME

        # Store the master Dark for later reference
        self.masterDark = masterDark

        return masterDark
    
    def create_master_flats(self, flatFiles=None, filterTypes=None, masterDark=None, masterBias=None):
        """
        Creates the master flat field matrices for all known flat files (unless flatFiles argument is
        passed) for all the known filters (unless filterTypes argument is passed). If a masterBias or
        masterDark matrix is provided, then these will be used in the construction of the master flats.
        If not, it uses its own versions. Returns the result as a list and stores it in the self.masterFlats
        attribute as well, to prevent having to construct it again.
        
        Keyword Args:
            flatFiles (list of strings): List of the absolute path to files from which the master dark
                                         should be constructed
            filterTypes (list of strings): List of the filters for which the master flats should be 
                                        constructed
            masterDark (numpy.ndarray): If specified, the master flats will be constructed using this
                                        master dark, instead of the default self.masterDark attribute
            masterBias (numpy.ndarray): If specified, the master flats will be constructed using this
                                        master bias, instead of the default self.masterBias attribute
            
        Returns:
            masterFlat (list of numpy.ndarray): returns a 3D matrix that represents the master flats.
                                                The master flat for each filter is stacked on the z-axis 
                                                (axis=2) in the same order as the specified filterTypes.
            
        """
        
        if flatFiles is None:
            flatFiles = self.flatFiles
            
        self.check_binning(flatFiles)
            
        if filterTypes is None:
            filterTypes = self.filters
            
        if masterDark is None:
            masterDark = self.masterDark
            
        if masterBias is None:
            masterBias = self.masterBias
        
        length, width = masterBias.shape
        
        # Variable that stores the master Flat for each filter type
        masterFlats = None

        # Each filter has its own masterFilter, so first we loop over each filter type
        for f in range(len(filterTypes)):
            filterType = filterTypes[f]

            stackedFlatData = None
            
            # Loop over each flat .fits file
            for i in range(len(flatFiles)):
                filename = flatFiles[i]

                # Open fits file and read the header from the first HDU object
                hduList = fits.open(filename)
                hdu = hduList[0]
                hduHeader = hdu.header
                
                # Get the width and length of the image
                NAXIS1 = hduHeader["NAXIS1"]
                NAXIS2 = hduHeader["NAXIS2"]

                # Check whether the data uses the same filter as we're currently interested in
                FILTER = hduHeader["FILTER"]
                if FILTER != filterType: continue  # If not, we continue to the next file

                # This block reads the EXPTIME keyword from the header
                EXPTIME = hduHeader["EXPTIME"]
                masterDarkScaled = masterDark * EXPTIME  # Scale the masterDark to the current exposure time
                
                # Correct the frame by subtracting bias and dark currents
                flatBiasDarkCorrected = hdu.data - masterBias - masterDarkScaled

                # Normalize the frame by dividing by the median value
                frameMedian = np.median(flatBiasDarkCorrected)
                flatNormalized = flatBiasDarkCorrected / frameMedian

                # On the first loop, assign the hdu content to the variable
                if stackedFlatData is None:
                    stackedFlatData = flatNormalized 
                # Afterwards, the content of each file can be stacked on axis=2
                else:
                    stackedFlatData = np.dstack((stackedFlatData, flatNormalized))

            # One-dimensionalize the stacked data if needed
            if len(flatFiles) > 1:
                # Gives the masterFlat for the current filter as the median
                masterFlat = np.median(stackedFlatData, axis=2)
            else:
                masterFlat = stackedFlatData
                
            #  Replace 0-values with something very small: 1e-100
            masterFlat = np.where(masterFlat==0, 1e-100, masterFlat)
            
            # Store this 2D masterFlat in the 3D list of masterFlats
            if masterFlats is None:
                masterFlats = masterFlat
            else:
                np.dstack((masterFlats, masterFlat))

        # Store the master Flats for later reference
        if filterTypes == self.filters:
            self.masterFlats = masterFlats
        
        return masterFlats
    
    
    # From here on, we only have dull getters and setters for the Observation attributes
    
    @property
    def foldername(self):
        return self._foldername
    
    @foldername.setter
    def foldername(self, foldername):
        self._foldername = foldername
            
    @property
    def files(self):
        return self._files
    
    @files.setter
    def files(self, files):
        self._files = files
    
    @property
    def masterBias(self):
        if self._masterBias is not None: return self._masterBias
        return self.create_master_bias()
    
    @masterBias.setter
    def masterBias(self, masterBias):
        self._masterBias = masterBias
        
    @property
    def masterDark(self):
        if self._masterDark is not None: return self._masterDark
        return self.create_master_dark()
    
    @masterBias.setter
    def masterDark(self, masterDark):
        self._masterDark = masterDark

    @property
    def masterFlats(self):
        if self._masterFlats is not None: return self._masterFlats
        return self.create_master_flats()
    
    @masterFlats.setter
    def masterFlats(self, masterFlats):
        self._masterFlats = masterFlats
        
    @property
    def lightFiles(self):
        return self._lightFiles
    
    @lightFiles.setter
    def lightFiles(self, lightFiles):
        self._lightFiles = lightFiles
    
    @property
    def biasFiles(self):
        return self._biasFiles
    
    @biasFiles.setter
    def biasFiles(self, biasFiles):
        self._biasFiles = biasFiles
    
    @property
    def darkFiles(self):
        return self._darkFiles
    
    @darkFiles.setter
    def darkFiles(self, darkFiles):
        self._darkFiles = darkFiles
    
    @property
    def flatFiles(self):
        return self._flatFiles
    
    @flatFiles.setter    
    def flatFiles(self, flatFiles):
        self._flatFiles = flatFiles
    
    @property
    def filters(self):
        return self._filterTypes
    
    @filters.setter
    def filters(self, filterTypes):
        self._filterTypes = filterTypes
        
class IncompatibleBinningError(Exception):
    """ Exception raised when a fits file has a different binning than 
        what was expected
        
        Attributes:
            file (string): the file that caused the error
            binning (string): the expected binning
            f_binning (string): the found binning            
    """
    
    def __init__(self, file, binning, f_binning):
        self.file = file
        self.binning = binning
        self.f_binning = f_binning
        self.message = f"{self.file}: expected {self.binning} binning but found {self.f_binning} binning"
        super().__init__(self.message)


# In[ ]:




