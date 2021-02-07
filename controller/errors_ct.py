class MissingFramesError(Exception):
    """ Exception raised when no suitable frames are found
        
        Attributes:
            message (string): message that will be displayed on throw        
    """
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)
        
class UnknownBinningError(Exception):
    """ Exception raised when something else than a 1x1 or 3x3 was encountered
        
        Attributes:
            message (string): message that will be displayed on throw        
    """
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)
        
class TooManyClustersError(Exception):
    """ Exception raised when the clustering of the files resulted in more than
        three seperate clusters. 
        
        Attributes:
            message (string): message that will be displayed on throw        
    """
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)
        
class SuitableMasterMissingError(Exception):
    """ Exception raised when no suitable master frame could be found near the 
        target datetime.
        
        Attributes:
            message (string): message that will be displayed on throw        
    """
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)