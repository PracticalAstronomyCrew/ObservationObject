import os

# Path constants associated with the telescope datadirs
tele_path = os.path.normpath("/net/vega/data/users/observatory/images/")
tele_subdirs = ("ST-7", "STL-6303E")
tele_subsubdirs = ("g", "i")

# User-specific path constants
base_path = os.path.normpath("/Users/users/gunnink/PAC/Data/")
raw_dir = "Raw"
reduced_dir = "Reduced"
correction_dir = "Correction"