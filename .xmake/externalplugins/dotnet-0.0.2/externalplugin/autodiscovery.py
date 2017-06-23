import os
import spi
import setupxmake

class AutoDiscovery(spi.ContentPlugin):

    def __init__(self, build_cfg):
        spi.ContentPlugin.__init__(self, build_cfg)

    # here the list of xmake plugins that are in conflict with this plugin
    def has_priority_over_plugins(self):
        return ()

    # evaluate the component source
    # should return whether it matches the content (true) or not (false).
    def matches(self):
        markerFile = os.path.join(self.build_cfg.component_dir(), "cfg", "dotnet.cfg")
        return os.path.isfile(markerFile)

    # Initialize BuildConfig object with script
    def setup(self):
        if self.matches():
            self.build_cfg._build_script_name=setupxmake.get_name()
            self.build_cfg.set_base_version(setupxmake.get_version())
            self.build_cfg.set_src_dir(self.build_cfg.component_dir())
            return True
        return False
