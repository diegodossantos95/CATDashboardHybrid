import os, xml.etree.ElementTree as ET
import log, spi, setupxmake
from os.path import join

class AutoDiscovery(spi.ContentPlugin):
    def __init__(self, build_cfg):
        spi.ContentPlugin.__init__(self, build_cfg)
	self._build_cfg=build_cfg
    
    def has_priority_over_plugins(self):
        return ()

    def matches(self):
	return False

    def setup(self):
	self.build_cfg._build_script_name = setupxmake.get_name()
        self.build_cfg.set_base_version(self.build_cfg.base_version())
        self.build_cfg.set_src_dir(self._build_cfg.component_dir())
        return True
