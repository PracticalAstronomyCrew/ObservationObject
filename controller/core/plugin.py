class Plugin(object):
    """ Base class for the Plugin object, from which each newly 
        implemented plugin should inherit. Each new plugin needs 
        to override two methods: __init__() and on_run(). In the 
        former only a small description of your plugin should be 
        given. In the latter, you should put the main logic of 
        your plugin. This method is called when the core functions 
        of the pipeline are finished.
    """

    def __init__(self):
        # Set some basic info for your plugin
        self.title = "The Base Plugin"
        self.description = "Acts as the superclass for all Plugins"
        
        # Do you want this plugin to be rerun when a better reduced
        # light file has become available? (Probably yes!)
        # I.e., does this plugin depend on reduced data?
        self.rerun_on_pending = True
        
        # Do you want this plugin to be rerun when astrometry results
        # come in? I.e., does this plugin depend on precise sky 
        # coordinates or other Astrometry header keywords?
        self.rerun_on_astrometry = True

    def on_run(self, obs, working_dir, args):
        """ Method that's called when the main pipeline is done. 
            You should override this method and implement the 
            functionalities of your plugin within this function. 
            Feel free to use already defined methods from the 
            Observation Object and the core pipeline files, but 
            do not rely on functions from other plugins. Instead,
            redefine them in here. This way, your plugin acts as
            a stand-alone extention to the pipeline.
            
            For compatiblity reasons, on_run() should call the 
            on_run_single() method when performing actions on a 
            specific file, unless on_run() handles files as part 
            of a group (such as for the Astrometry plugin).
        """
        # This is a quick example on how you could call on_run_single()
        for file in obs.lightFiles:
            self.on_run_single(obs, working_dir, args, file)
        
        raise NotImplementedError
        
    def on_run_single(self, obs, working_dir, args, file):
        """ Method that is meant for the performing the main 
            operation of your plugin, for a specific file. This 
            method is called by on_run(), or when a better 
            version of this file becomes available through the 
            pending mechanism or the astrometry queue.
            
            Because of these last two reasons, explicitly check 
            any incoming files! I.e., if your plugin acts on light 
            frames only, then please check in this method again 
            if the passed file is really a light file and not any
            other file or frame type.
        """
        # Note how on_run() passes light files only, but by checking 
        # it again here, we can be sure that the pending mechanism 
        # and the astronomy queue can also call this plugin!
        if file in obs.lightFiles:
            # Place all your logic here, or in new methods of course
            print(f"I found a light frame! It's called {file}")
        
        raise NotImplementedError