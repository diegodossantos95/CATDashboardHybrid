import os
import spi
import setupxmake
import subprocess

class AutoDiscovery(spi.ContentPlugin):

    def __init__(self, build_cfg):
        spi.ContentPlugin.__init__(self, build_cfg)

    # here the list of xmake plugins that are in conflict with this plugin
    def has_priority_over_plugins(self):
        return ()

    # evaluate the component source
    # should return whether it matches the content (true) or not (false).
    def matches(self):
        markerFile = os.path.join(self.build_cfg.component_dir(), "build.sbt")
        if self.build_cfg.alternate_path() != None:
            markerFile = os.path.join(self.build_cfg.alternate_path(), "build.sbt")
        return os.path.isfile(markerFile)

    # Initialize BuildConfig object with script
    def setup(self):
        if self.matches():
            self.build_cfg._build_script_name=setupxmake.get_name()
            self.build_cfg.set_base_version(self._get_version()) #the version of the project to build
            self.build_cfg.set_src_dir(self.build_cfg.component_dir())
            return True
        return False

    # The version is retrieved later for real via a call to SBT
    def _get_version(self):
        return 'NONE'
