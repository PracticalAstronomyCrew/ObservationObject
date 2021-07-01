# ==============================================================================
#                                L I C E N S E
# ==============================================================================
#
# Copyright (c) 2020 Adrian Bittner
#
# This software is provided as is without any warranty whatsoever. Permission to
# use, for non-commercial purposes is granted. Permission to modify for personal
# or internal use is granted, provided this copyright and disclaimer are included
# in all copies of the software. Redistribution of the code, modified or not, is
# not allowed. All other rights are reserved.     
#
# ==============================================================================
#
# Slightly edited to allow for Jupyter Notebook use and double line replacement.
# 28-06-2020 Fabian Gunnink
#
# ==============================================================================

import sys

import logging
logger = logging.getLogger(__name__)

def progressBar(iteration, total, outputlabel, prefix='', suffix='', decimals=2, barLength=80, color='g'):
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

    filledLength    = int(round(barLength * iteration / float(total)))
    percents        = round(100.00 * (iteration / float(total)), decimals)
    bar             = color + ' '*filledLength + '\033[49m' + ' '*(barLength - filledLength - 1)
    print(("[ "+'\033[0;37m'+"RUNNING "+'\033[0;39m'+"] " + outputlabel + '{:<80}').format(' ') + '%s |%s| %s%s %s' % (prefix, bar, percents, '%', suffix), end="\r", flush=True)
    logging.info(outputlabel)

def module(outputlabel):
    """
    Print the name of the currently active module. 

    Parameters: 
        outputlabel - Required: Message to be printed (str)
    """
    sys.stdout.write("\033[0;37m"+outputlabel+"\033[0;39m")
    sys.stdout.flush(); print("")
    
    logging.info(outputlabel)

def newline():
    print("")

def running(outputlabel):
    """
    Print a new message to stdout with the tag "Running". 

    Parameters:
        outputlabel - Required: Message to be printed (str)
    """
    print("[ "+'\033[0;37m'+"RUNNING "+'\033[0;39m'+"] " + outputlabel, end="\r", flush=True)
    logging.info(outputlabel)

def runningBar(outputlabel):
    """
    Print a new message to stdout with the tag "Running". 

    Parameters:
        outputlabel - Required: Message to be printed (str)
    """
    print("[ "+'\033[0;37m'+"RUNNING "+'\033[0;39m'+"] " + outputlabel, flush=True)
    logging.info(outputlabel)

def updateBarDone(outputlabel):
    """
    Overwrite the previous message in stdout with the tag "Done" and a new message. 

    Parameters: 
        outputlabel - Required: Message to be printed (str)
        progressbar - Optional: Set True if the previous message was the progress bar (bool)
    """
    print(("[ "+'\033[0;32m'+"DONE    "+'\033[0;39m'+"] "+outputlabel + '{:<80}').format(' ') + (" " + '{:<120}').format(' '), flush=True)
    logging.info(outputlabel)

def updateDone(outputlabel):
    """
    Overwrite the previous message in stdout with the tag "Done" and a new message. 

    Parameters: 
        outputlabel - Required: Message to be printed (str)
        progressbar - Optional: Set True if the previous message was the progress bar (bool)
    """
    print("[ "+'\033[0;32m'+"DONE    "+'\033[0;39m'+"] "+outputlabel, flush=True)
    logging.info(outputlabel)

def done(outputlabel):
    """
    Print a new message to stdout with the tag "Done". 

    Parameters: 
        outputlabel - Required: Message to be printed (str)
    """
    sys.stdout.write("\r\r[ "+'\033[0;32m'+"DONE    "+'\033[0;39m'+"] "+outputlabel)
    sys.stdout.flush(); print("")
    logging.info(outputlabel)

def updateWarning(outputlabel, progressbar=False):
    """
    Overwrite the previous message in stdout with the tag "Warning" and a new message. 

    Parameters: 
        outputlabel - Required: Message to be printed (str)
        progressbar - Optional: Set True if the previous message was the progress bar (bool)
    """
    if progressbar == True:
        sys.stdout.write("\033[K")
    sys.stdout.write("\033[F"); sys.stdout.write("\033[K")
    sys.stdout.write("\r\r [ "+'\033[0;33m'+"WARNING "+'\033[0;39m'+"] "+outputlabel)
    sys.stdout.flush(); print("")
    logging.warning(outputlabel)

def warning(outputlabel):
    """
    Print a new message to stdout with the tag "Warning". 

    Parameters: 
        outputlabel - Required: Message to be printed (str)
    """
    sys.stdout.write("\r\r [ "+'\033[0;33m'+"WARNING "+'\033[0;39m'+"] "+outputlabel)
    sys.stdout.flush(); print("")
    logging.warning(outputlabel)

def updateFailed(outputlabel, progressbar=False):
    """
    Overwrite the previous message in stdout with the tag "Failed" and a new message. 

    Parameters: 
        outputlabel - Required: Message to be printed (str)
        progressbar - Optional: Set True if the previous message was the progress bar (bool)
    """
    if progressbar == True:
        sys.stdout.write("\033[K")
    sys.stdout.write("\033[F"); sys.stdout.write("\033[K")
    sys.stdout.write("\r\r [ "+'\033[0;31m'+"FAILED  "+'\033[0;39m'+"] "+outputlabel)
    sys.stdout.flush(); print("")
    logging.error(outputlabel)

def failed(outputlabel):
    """
    Print a new message to stdout with the tag "Failed". 

    Parameters: 
        outputlabel - Required: Message to be printed (str)
    """
    sys.stdout.write("\r\r [ "+'\033[0;31m'+"FAILED  "+'\033[0;39m'+"] "+outputlabel)
    time.sleep(0)
    sys.stdout.flush(); print("")
    time.sleep(0)
    logging.error(outputlabel)