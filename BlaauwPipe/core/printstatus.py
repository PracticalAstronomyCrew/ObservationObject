# # ==============================================================================
# #                                L I C E N S E
# # ==============================================================================
# #
# # Copyright (c) 2020 Adrian Bittner
# #
# # This software is provided as is without any warranty whatsoever. Permission to
# # use, for non-commercial purposes is granted. Permission to modify for personal
# # or internal use is granted, provided this copyright and disclaimer are included
# # in all copies of the software. Redistribution of the code, modified or not, is
# # not allowed. All other rights are reserved.     
# #
# # ==============================================================================
# #
# # Slightly edited to allow for Jupyter Notebook use and double line replacement.
# # 29-06-2020 Fabian Gunnink
# #
# # ==============================================================================

import sys
from datetime import datetime

import logging
logger = logging.getLogger(__name__)

def progressBar(iteration, total, prefix='', suffix='', decimals=2, barLength=80, color='g', log=True):
    """
    Call in a loop to create a progress bar in the terminal.

    Parameters:
        iteration - Required: current iteration (int)
        total     - Required: total iterations (int)
        prefix    - Optional: prefix string (str)
        suffix    - Optional: suffix string (str)
        decimals  - Optional: number of printed decimals (int)
        barLength - Optional: length of the progress bar in the terminal (int)
        color     - Optional: color identifier (str)
    """
    if   color == 'y': color = '\033[43m'
    elif color == 'k': color = '\033[40m'
    elif color == 'r': color = '\033[41m'
    elif color == 'g': color = '\033[42m'
    elif color == 'b': color = '\033[44m'
    elif color == 'm': color = '\033[45m'
    elif color == 'c': color = '\033[46m'
        
    percents        = round(100.00 * (iteration / float(total)), decimals)
    filledLength    = int(round(barLength * iteration / float(total)))
    bar             = color + ' '*filledLength + '\033[49m' + ' '*(barLength - filledLength - 1)
    now             = datetime.now().isoformat(sep=' ', timespec='milliseconds').split(" ")[1]
    if iteration != 0:
        sys.stdout.write("\033[F")

    sys.stdout.write(("\r{} [ ".format(now) + ('\033[0;37m'+"RUNNING "+'\033[0;39m'+"] {}\n |{}| {:.2f}{} {}\r")).format(prefix, bar, percents, '%', suffix)),
    sys.stdout.flush()
    if log: logging.info(prefix, stacklevel=3)

def module(outputlabel, log=True):
    """
    Print the name of the currently active module. 

    Parameters: 
        outputlabel - Required: Message to be printed (str)
    """
    sys.stdout.write("\033[0;37m"+outputlabel+"\033[0;39m")
    sys.stdout.flush(); print("")
    if log: logging.info(outputlabel, stacklevel=3)

def running(outputlabel, log=True):
    """
    Print a new message to stdout with the tag "Running". 

    Parameters:
        outputlabel - Required: Message to be printed (str)
    """
    now = datetime.now().isoformat(sep=' ', timespec='milliseconds').split(" ")[1]
    sys.stdout.write("\r{} [ ".format(now)+'\033[0;37m'+"RUNNING "+'\033[0;39m'+"] " + "{:<10}".format(outputlabel))
    sys.stdout.flush(); print("")
    if log: logging.info(outputlabel, stacklevel=3)

def updateDone(outputlabel, progressbar=False, log=True):
    """
    Overwrite the previous message in stdout with the tag "Done" and a new message. 

    Parameters: 
        outputlabel - Required: Message to be printed (str)
        progressbar - Optional: Set True if the previous message was the progress bar (bool)
    """
    if progressbar == True:
        sys.stdout.write("\033[K")
    now = datetime.now().isoformat(sep=' ', timespec='milliseconds').split(" ")[1]
    sys.stdout.write("\033[F"); sys.stdout.write("\033[K")
    sys.stdout.write("\r\r{} [ ".format(now)+'\033[0;32m'+"DONE    " + '\033[0;39m'+"] {}".format(outputlabel))
    sys.stdout.flush(); print("")
    if log: logging.info(outputlabel, stacklevel=3)

def done(outputlabel, log=True):
    """
    Print a new message to stdout with the tag "Done". 

    Parameters: 
        outputlabel - Required: Message to be printed (str)
    """
    now = datetime.now().isoformat(sep=' ', timespec='milliseconds').split(" ")[1]
    sys.stdout.write("\r\r{} [ ".format(now)+'\033[0;32m'+"DONE    "+'\033[0;39m'+"] "+outputlabel)
    sys.stdout.flush(); print("")
    if log: logging.info(outputlabel, stacklevel=3)

def updateWarning(outputlabel, progressbar=False, log=True):
    """
    Overwrite the previous message in stdout with the tag "Warning" and a new message. 

    Parameters: 
        outputlabel - Required: Message to be printed (str)
        progressbar - Optional: Set True if the previous message was the progress bar (bool)
    """
    now = datetime.now().isoformat(sep=' ', timespec='milliseconds').split(" ")[1]
    if progressbar == True:
        sys.stdout.write("\033[K")
    sys.stdout.write("\033[F"); sys.stdout.write("\033[K")
    sys.stdout.write("\r\r{} [ ".format(now)+'\033[0;33m'+"WARNING "+'\033[0;39m'+"] "+outputlabel)
    sys.stdout.flush(); print("")
    if log: logging.warning(outputlabel, stacklevel=3)

def warning(outputlabel, log=True):
    """
    Print a new message to stdout with the tag "Warning". 

    Parameters: 
        outputlabel - Required: Message to be printed (str)
    """
    now = datetime.now().isoformat(sep=' ', timespec='milliseconds').split(" ")[1]
    sys.stdout.write("\r\r{} [ ".format(now)+'\033[0;33m'+"WARNING "+'\033[0;39m'+"] "+outputlabel)
    sys.stdout.flush(); print("")
    if log: logging.warning(outputlabel, stacklevel=3)

def updateFailed(outputlabel, progressbar=False, log=True):
    """
    Overwrite the previous message in stdout with the tag "Failed" and a new message. 

    Parameters: 
        outputlabel - Required: Message to be printed (str)
        progressbar - Optional: Set True if the previous message was the progress bar (bool)
    """
    now = datetime.now().isoformat(sep=' ', timespec='milliseconds').split(" ")[1]
    if progressbar == True:
        sys.stdout.write("\033[K")
    sys.stdout.write("\033[F"); sys.stdout.write("\033[K")
    sys.stdout.write("\r\r{} [ ".format(now)+'\033[0;31m'+"FAILED  "+'\033[0;39m'+"] "+outputlabel)
    sys.stdout.flush(); print("")
    if log: logging.critical(outputlabel, stacklevel=3)

def failed(outputlabel, log=True):
    """
    Print a new message to stdout with the tag "Failed". 

    Parameters: 
        outputlabel - Required: Message to be printed (str)
    """
    now = datetime.now().isoformat(sep=' ', timespec='milliseconds').split(" ")[1]
    sys.stdout.write("\r\r{} [ ".format(now)+'\033[0;31m'+"FAILED  "+'\033[0;39m'+"] "+outputlabel)
    sys.stdout.flush(); print("")
    if log: logging.info(critical, stacklevel=3)

def newline():
    print("")
