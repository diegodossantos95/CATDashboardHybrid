import os, xml.etree.ElementTree as ET
import log, spi, setupxmake
from os.path import join

class AutoDiscovery(spi.ContentPlugin):

    def __init__(self, build_cfg):
        spi.ContentPlugin.__init__(self, build_cfg)
	self._build_cfg=build_cfg

    # here the list of xmake plugins that are in conflict with this plugin
    def has_priority_over_plugins(self):
        return ('maven',) # xmake maven plugin looks at pom.xml file in project to be activated
                          # so indicate to xmake to ignore the maven plugin during the phase of autodiscovery

    def matches(self):
	log.debug('Checking pom.xml if it is a MiOS build type ...')
	project_dir = self._build_cfg.component_dir()
	maxDepth =False
	#Find if there is an argument sent from Project portal to check for the max poms, then alter the level
	if self.build_cfg.build_args():
        	for arg in self.build_cfg.build_args():
        		if(arg.startswith('-Dsearch-max-pom')):
        			values = arg.split('=')
				log.debug('search-max-pom',values[0])
				log.debug('search-max-pom',values[1])
        			if(values[1] == 'true'):
					maxDepth =True

	#End of maxPom search logic
	level =2
	pomfile = 'pom.xml'
	f = join(self._build_cfg.component_dir(),pomfile)
	if os.path.isfile(f):
		log.debug('pom file: '+f)
		tree = ET.parse(f)
		pomroot = tree.getroot()
		for child in pomroot:
			if child.tag.find("packaging") >= 0 and child.text.find("xcode") >=0:
				log.debug('Project identified to be MiOS build type ....')
				return True
	else:
		log.debug('Not MiOS type of build.No pom.xml found at project root level ...')
		return False
	log.debug('maxDepth',maxDepth)	
	if(not maxDepth):
		log.debug('pom.xml to be verified till level ',level,' from project root directory')
	else:
		log.debug('------search-max-pom is sent and is true so maximum level of folders will be searched to find if it is MiOS build')
	log.debug('Now searching for pom.xml having xcode pacgking type in the src folder')
	project_dir = project_dir.rstrip(os.path.sep)
	if os.path.isdir(project_dir):
		num_sep = project_dir.count(os.path.sep)
		for root, dirs, files in os.walk(project_dir):
			f=join(root,pomfile)
			if os.path.isfile(f):
				log.debug('pom file: '+f)
				tree = ET.parse(f)
				pomroot = tree.getroot()
				for child in pomroot:
					if child.tag.find("packaging") >= 0 and child.text.find("xcode") >=0:
						log.info('Project identified to be MiOS build type ...')
						return True
			num_sep_this = root.count(os.path.sep)
			if not maxDepth and  num_sep + level <= num_sep_this:
				del dirs[:]
	
	log.info('Project not found to be MiOS build type ...')
        return False

    def setup(self):
        if self.matches():
            self.build_cfg._build_script_name = setupxmake.get_name()
            log.info('For mios project version will be resolved at build time')
            self.build_cfg.set_base_version('NONE')
            self.build_cfg.set_src_dir(self._build_cfg.component_dir())
            return True
        return False
