import os, xml.dom.minidom as minidom
import log, spi, setupxmake
from os.path import join

class AutoDiscovery(spi.ContentPlugin):

    def __init__(self, build_cfg):
        spi.ContentPlugin.__init__(self, build_cfg)

    def has_priority_over_plugins(self):
        return ()

    def matches(self):
        f = join(self.build_cfg.component_dir(), 'src', 'config.xml')

        if os.path.isfile(f):
            log.info('config.xml found in src folder')
            parsed_xml = minidom.parse(f)
            if parsed_xml.firstChild.hasAttribute('xmlns:cdv'):
                log.info('Project identified as Cordova...')
                return True

        log.info('Project not identified as Cordova build...')
        return False

    def setup(self):
        if self.matches():
            self.build_cfg._build_script_name=setupxmake.get_name()
            # Version will be resolved at build time from Cordova config.xml
            self.build_cfg.set_base_version('NONE')
            self.build_cfg.set_src_dir(os.path.join(self.build_cfg.component_dir(), 'src'))
            return True
        return False
