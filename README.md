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

- :white_check_mark: Copy raw files to backup directory
- :white_check_mark: Create and save the raw correction frames
  - :white_check_mark: Generate frame types (Bias, Dark, Flat field)
  - :white_check_mark: Cleverly classify correction frames in clusters based on creation time
  - :white_check_mark: Keep track of binning and filters
- :white_check_mark: Reduce and save light frames
  - :white_check_mark: Reduce images using the closest correction frame clusters
  - :white_check_mark: Append information about reduction process in header
- :heavy_check_mark: Re-reduce frames when more recent correction frames have become available
- [ ] Run frames through Astrometry
  - [ ] Alternate between raw & reduced when Astrometry fails
  - [ ] Save new information inside header
- [ ] Add new header keywords
  - :heavy_check_mark: Reference files used for all performed processes
  - :heavy_check_mark: STARALT info
- [ ] Generate log about the performed actions


The Pending Mechanism
-------------------
The pending mechanism is an independent extension to the Controller that is responsible for updating already reduced frames. When a better master correction frame becomes available than was used in the reduction of a certain frame, then this file will be reduced again with the new master correction. This process can hence guarantee that the reduced version is the best one possible.

During the original reduction process, the Controller keeps track of the relative ages of the master correction frames used. If every observation night always contained the necessary correction frames, then these relative ages would always be zero. This is however not the case. Flat fields for a specific filter could be missing for example. The Controller tries to take care of this by looking into 'nearby' directories: it tries to find compatible correction frames taken a few days earlier or later than the actual observation. Past frames are, of course, always available. But what about future nights? These might contain better correction frames!

The Pending Mechanism takes care of this. If the relative bias/dark/flat age of a reduced file is not 0 for all three, then this file is added to "pending_log.csv". Besides some rather basic info about this frame, it also states an expiration date. This is the latest date at which we can hope to find better correction frames. The Pending Mechanism reads the log file everyday and either finds new frames and reduces the frame again, or it fails and re-appends this frame to the log. If it has expired, we can no longer hope to find a better version than the current reduced frame, ever. Any expired entries are hence removed upon reading the log.


Header keywords
-------------
The Controller adds new header keywords during correction frame creation and reduction. For the sake of completeness, here follows a list of the introduced keywords, where they can be found and what they mean.

| Frame type         | Header Keyword | Meaning        | Used        | 
|--------------------|----------------|----------------|-------------|
| Bias/Dark/Flat     | KW-SRCN        | The number of frames used for generating this master correction frame | :white_check_mark:
| Bias/Dark/Flat     | KW-SRC#        | Gives the path to the #'th frame used in the frame generation. The # can be replaced with an integer up to the value in KW-SRCN. For example, the header keyword KW-SRC1 gives the path to the first file used. | :white_check_mark: 
|Dark/Flat/Light     | KW-MBAGE       | Gives the number of days between the creation time of the current frame and the bias frame used in the reduction process. | :white_check_mark:
|Flat/Light          | KW-MDAGE       | Gives the number of days between the creation time of the current frame and the dark frame used in the reduction process. | :white_check_mark:
|Light               | KW-MFAGE       | Gives the number of days between the creation time of the current frame and the flat field used in the reduction process. | :white_check_mark:
|Light               | KW-MBIAS         | The path to the master bias that was used in the reduction process. | :white_check_mark:
|Light               | KW-MDARK         | The path to the master dark that was used in the reduction process. | :white_check_mark:
|Light               | KW-MFLAT         | The path to the master flat that was used in the reduction process. | :white_check_mark:


Naming conventions
-----------------
Original names are preserved as much as possible. Master correction frames are however newly generated, so these files use custom naming. Currently, these custom naming conventions are as follows:

```master_{frame_type}{binning}{filter iff flat}C{cluster}.fits```

So, a master bias corresponding to the second bias cluster and a binning of 3x3 looks like:

```master_bias3x3C2.fits```

And a master flat taken in the H-alpha filter with a binning of 1x1 found in the first cluster would be:

```master_flat1x1H-alphaC1.fits```

Although information about the frame type, binning and filter is also accessible through the right header keywords, this naming convention also enables actual humans to quickly know what file they're looking at.