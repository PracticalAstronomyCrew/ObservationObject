The BlaauwPipe
======================
The BlaauwPipe is the unofficial data pipeline specifically designed for the Blaauw Observatory and (soon) the Dark Sky Park Lauwersmeer Observatory. It aims at unifying all important reduction processes and mechanisms into a single Python program, built in such a way to be compatible with all (read: most) observation nights. The BlaauwPipe is built upon a plugin framework, meaning that additional modules with extra pieces of code can easily be added and configured with the pipeline, without having to dive deep into the source code.

The pipeline heavily depends on the ObservationObject class, an instance of which gives the user direct access to all files from the original observation night, as well as a set of useful methods that makes working with telescope data easier. Although the PipelineResult object is but a simple subclass of the ObservationObject, it greatly simplifies storing the pipeline results in a dedicated environment. The BlaauwPipe is hence a delicate interplay between the ObservationObject and PipelineResult, connected by the algorithms defined in the Core and External plugins.

![Superfancy sneak-preview](https://drive.google.com/uc?export=view&id=1W9rSDwJ5H8bVvrxbFYcV0JI20_2rm_lL)

Current Plugin Collection
--------------
The table below gives an overview of the currently implemented/anticipated modules that the BlaauwPipe runs by default. A difference is made between two plugin types: the core plugins and the external plugins. The former are absolutely necessary pieces of code that need to be run on every observation at least once, while the latter give access to additional information or an improved analysis.

| <img width=20/> Plugin <img width=20/> | Type | Goal        |
|--------------------------------|--------------------------------|----------------|
| The Backup-Maker | Core          | Copies content from observation directory to new environment. |
| The Correction-Creator | Core           | Create correction frames for each image type, cluster, binning and, if applicable, filter. |
| The Fits-Reducer | Core           | Reduces light files with the best suitable correction frames. Also implements the Pending Mechanism. |
| The Astrometry-Uploader | Core | Run (reduced & raw) light files through Astrometry and appends WCS data to header. |
| Airmass (unfinished) | External | Calculates airmass for every light frame and appends result as a header keyword. |
| Fixer (unfinished) | External | Rectifies human mistakes by e.g. correction header keywords, based on some log. |
| Preview (unfinished) | External | Generates greyscale/RGB .png images from light files. |


Roadmap
--------------
The current list of (intended) features include:

- :heavy_check_mark: Copy raw files to backup directory
- :heavy_check_mark: Create and save the raw correction frames
  - :heavy_check_mark: Generate frame types (Bias, Dark, Flat field)
  - :heavy_check_mark: Cleverly classify correction frames in clusters based on creation time
  - :heavy_check_mark: Keep track of binning and filters
- :heavy_check_mark: Reduce and save light frames
  - :heavy_check_mark: Reduce images using the closest correction frame clusters
  - :heavy_check_mark: Append information about reduction process in header
  - :white_check_mark: Re-reduce frames when more recent correction frames have become available (The Pending Mechanism, see below)
- :white_check_mark:  Run frames through Astrometry
   - :white_check_mark: Uploading through API (astrometry-net-client)
  - :white_check_mark: Save new information inside header
  - [ ] Alternate between raw & reduced when Astrometry fails
  - [ ] Introduce an Astrometry-specific Pending Mechanism
- :white_check_mark:  Add new header keywords
  - :white_check_mark: Reference files used for all performed processes
  - :white_check_mark: STARALT info
- :white_check_mark:  Generate full log of performed actions
- :white_check_mark:  Improve stability of Plugin framework
  - :white_check_mark: Plugin call order customizable
  - [ ] Semi-automic error catching

The Pending Mechanism
-------------------
The pending mechanism is an independent extension to the BlaauwPipe that is responsible for updating already reduced frames. When a better master correction frame becomes available than was used in the reduction of a certain frame, then this file will be reduced again with the new master correction. This process can hence guarantee that the reduced version is the best one possible.

During the original reduction process, the BlaauwPipe keeps track of the relative ages of the master correction frames used. If every observation night always contained the necessary correction frames, then these relative ages would always be zero. This is however not the case. Flat fields for a specific filter could be missing for example. The BlaauwPipe tries to take care of this by looking into 'nearby' directories: it tries to find compatible correction frames taken a few days earlier or later than the actual observation. Past frames are, of course, always available. But what about future nights? These might contain better correction frames!

The Pending Mechanism takes care of this. If the relative bias/dark/flat age of a reduced file is not 0 for all three, then this file is added to "pending_log.csv". Besides some rather basic info about this frame, it also states an expiration date. This is the latest date at which we can hope to find better correction frames. The Pending Mechanism reads the log file everyday and either finds new frames and reduces the frame again, or it fails and re-appends this frame to the log. If it has expired, we can no longer hope to find a better version than the current reduced frame, ever. Any expired entries are hence removed upon reading the log.


Header keywords
-------------
The BlaauwPipe adds new header keywords during correction frame creation and reduction. For the sake of completeness, here follows a list of the introduced keywords, where they can be found and what they mean.

| Header Keyword <img width=100/>| Frame type <img width=250/>    | Meaning        |
|--------------------------------|--------------------------------|----------------|
| KW-TRAW                        | Bias/Dark/Flat/Light           | Path to the raw version of this file as stored on the telescope dataserver |
| KW-PRAW                        | Bias/Dark/Flat/Light           | Path to the raw version of this file as stored on the pipeline dataserver  |
| KW-PRED                        | Bias/Dark/Flat/Light           | Path to the reduced version of this file as stored on the pipeline dataserver  |
| KW-SRCN                        | (Mas.) Bias/Dark/Flat          | The number of frames used for generating this master correction frame |
| KW-SRC#                        | (Mas.) Bias/Dark/Flat          | Gives the path to the #'th frame used in the frame generation. The # can be replaced with an integer up to the value in KW-SRCN. For example, the header keyword KW-SRC1 gives the path to the first file used. |
| KW-MBAGE                       | (Mas.) Dark/Flat/ (Red.) Light | Gives the number of days between the creation time of the current frame and the bias frame used in the reduction process. |
| KW-MDAGE                       | (Mas.) Flat/ (Red.) Light      | Gives the number of days between the creation time of the current frame and the dark frame used in the reduction process. |
| KW-MFAGE                       | (Red.) Light                   | Gives the number of days between the creation time of the current frame and the flat field used in the reduction process. |
| KW-MBIAS                       | (Red.) Light                   | The path to the master bias that was used in the reduction process. |
| KW-MDARK                       | (Red.) Light                   | The path to the master dark that was used in the reduction process. |
| KW-MFLAT                       | (Red.) Light                   | The path to the master flat that was used in the reduction process. |


Naming conventions
-----------------
Original names are preserved as much as possible. Master correction frames are however newly generated, so these files use custom naming. Currently, these custom naming conventions are as follows:

```master_{frame_type}{binning}{filter iff flat}C{cluster}.fits```

So, a master bias corresponding to the second bias cluster and a binning of 3x3 looks like:

```master_bias3x3C2.fits```

And a master flat taken in the H-alpha filter with a binning of 1x1 found in the first cluster would be:

```master_flat1x1H-alphaC1.fits```

Although information about the frame type, binning and filter is also accessible through the right header keywords, this naming convention also enables actual humans to quickly know what file they're looking at.
