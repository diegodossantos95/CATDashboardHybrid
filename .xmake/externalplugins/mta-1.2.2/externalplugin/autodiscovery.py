'''
Created on 27.03.2015

@author: I051432
'''
import os, xml.etree.ElementTree as ET
import log, spi, setupxmake
from os.path import join

from common import load_yaml, initialize_src
from content.maven import content as MavenDiscovery
from content.node import content as NodeDiscovery

class AutoDiscovery(spi.ContentPlugin):

    def __init__(self, build_cfg):
        spi.ContentPlugin.__init__(self, build_cfg)

    # here the list of xmake plugins that are in conflict with this plugin
    # Disabling has_priority_over_plugins because maven & node have bigger priority 
    # def has_priority_over_plugins(self):
    #    return ('maven', 'node',)  # xmake maven plugin looks at pom.xml file in project to be activated
                          # so indicate to xmake to ignore the maven plugin during the phase of autodiscovery

    def matches(self):
    	f = join(self.build_cfg.component_dir(), "mta.yaml")
        log.debug('Checking mta.yaml exists for MTA build type in "{}"...'.format(f))
        if os.path.isfile(f):
            log.info('Project identified to be MTA build type ...')
            maven_discovery=MavenDiscovery(self.build_cfg,None)
            node_discovery=NodeDiscovery(self.build_cfg,None)
            if maven_discovery.matches() or node_discovery.matches():
                log.warning('But maven or node project detected in the same directory, MTA plugin must be forced if needed')
                return False
            return True
    	
        log.info('Project not found to be MTA build type ...')
        return False
            
    def setup(self):
        if self.matches():
            self.build_cfg._build_script_name = setupxmake.get_name()
            return True
        return False
