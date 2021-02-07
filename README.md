The Observation Object
======================
This python class enables the user to quickly gain control over the data of an observation night. To initialise
an Observation object, only the telescope data directory needs to be passed to the class constructor. Generating
the master correction frames for the corresponding night is then as simple as calling a method on your newly 
created Observation object. This file contains more information about this procedure. Besides the Observation 
object itself, the Controller script is introduced.

Creating the Observation object
--------------------------------
bla

The Controller
--------------
The Controller script acts as a wrapper for the Observation class, specifically designed for its purposes in the
data pipeline. The current list of (intended) features include:

- [X] Copy raw files to backup directory
- [X] Create and save the raw correction frames
  - [X] Generate frame types (Bias, Dark, Flat field)
  - [X] Cleverly classify correction frames in clusters based on creation time
  - [X] Keep track of binning and filters
- [X] Reduce and save light frames
  - [X] Reduce images using the closest correction frame clusters
  - [X] Append information about reduction process in header
- [ ] Run frames through Astrometry
  - [ ] Alternate between raw & reduced when Astrometry fails
  - [ ] Save new information inside header
- [ ] Add new header keywords
  - [~] Reference files used for all performed processes
  - [~] STARALT info
- [ ] Generate log about the performed actions
