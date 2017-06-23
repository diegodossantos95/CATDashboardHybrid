'''
Created on 27.03.2015

@author: I051432
'''
import utils
import log
import os
import xml.etree.ElementTree as ET
import inst
import re
import shlex
import subprocess
import urllib2
import shutil
import contextlib
import json
import tarfile

from urlparse import urlparse
from tempfile import NamedTemporaryFile
from artifact import Artifact
from string import Template
from ExternalTools import OS_Utils
from os import path,unlink
from os.path import join, isfile
from xmake_exceptions import XmakeException
#from spi import JavaBuildPlugin
import spi
import shutil
import json
import sys
import glob

from common import initialize_src
from MtaTools import MavenTool, NodeTool, GruntTool

class BuildPlugin(spi.JavaBuildPlugin):
    '''
        Xmake maven plugin class that provides the ability to build maven project
    '''
    RESERVED_OPTIONS = ()

    ###############################################################################
    #  PLUGIN initialization
    ###############################################################################
    def __init__(self, build_cfg):
        spi.JavaBuildPlugin.__init__(self, build_cfg)

        self._bundle = False
        self._mta_extension = None
        self._mtar_build_target="XSA"
        self.build_cfg.set_base_group("com.sap.prd.xmake.example.mtars")
        self._node_version = '0.12.0'
        self._node_toolid = 'com.sap.prd.distributions.org.nodejs.{}:nodejs'.format(utils.runtime())
        self._npm_tool=None
        
        self._maven_version = '3.3.3'
        self._maven_toolid = 'org.apache.maven:apache-maven'
        self._maven_tool=None
        
        self._grunt_tool=None        
        
        self._mta_version = 'latest'
        self._mta_group_artifact = 'com.sap.mta:mta_archive_builder'        
        self._mta_user_options=[]

        self._mta_returned=dict()
        self._copied_src_dir = join(self.build_cfg.temp_dir(), 'src')
        
        self._ads = join(self.build_cfg.temp_dir(), 'export.ads')
        self.build_cfg.set_export_script(self._ads)
        
        self._do_build=True if self.build_cfg.profilings() is None else False
        
        self.build_cfg.set_base_version("NONE")
        

    def java_set_option(self,o,v):
        if o == 'maven-version' or o == 'version':
            log.info( '\tusing maven version ' + v)
            self._maven_version = v
        # enhances this plugin to be able to specify the group:artifact of maven in config .xmake.cfg
        elif o == 'maven-group-artifact':
            log.info( '\tusing maven ' + v)
            self._maven_toolid = v
        elif o == 'node-version':
            log.info( '\tusing node version ' + v)
            self._node_version = v
        # enhances this plugin to be able to specify the group:artifact of maven in config .xmake.cfg
        elif o == 'node-group-artifact':
            log.info( '\tusing node ' + v)
            self._node_toolid = v
        elif o == 'mta-version':
            log.info( '\tusing mta version ' + v)
            self._mta_version = v
        # enhances this plugin to be able to specify the group:artifact of maven in config .xmake.cfg
        elif o == 'mta-group-artifact':
            log.info( '\tusing mta ' + v)
            self._mta_group_artifact = v
        elif o == 'mtar-group':
            log.info( '\tgroup for storing mtar will be ' + v)
            self.build_cfg.set_base_group(v)        
        elif o == 'mtar-build-target':
            log.info( '\tbuild-target is ' + v)
            self._mtar_build_target = v
        elif o == 'mta-extension':
            log.info( '\tmta-extension is ' + v)
            self._mta_extension = v
        elif o == 'bundle':
            self._bundle = (v == 'true')
        elif o =='options':
            values = v.split(',')
            for value in values:
                log.info( '\tusing custom option ' + value)
                if value not in BuildPlugin.RESERVED_OPTIONS:
                    self._mta_user_options.append(value)
                else:
                    log.warning('\tignoring custom option {}. Only xmake can manage this option.'.format(value))
        else:
            if o is not None: v="%s=%s"%(o,v) # does not correspond to one of the option above remangle it as originally splitted by JavaBuildPlugin if it was containing an equal char
            log.info( '\tusing custom option ' + v)
            self._mta_user_options.append(v)

    def plugin_imports(self):
        
        if self._mta_version and self._mta_version.lower()=="latest" and self.build_cfg.import_repos() and self.build_cfg.import_repos()[0]:
            o=urlparse(self.build_cfg.import_repos()[0])        
            repoId=o.path.strip('/').split('/')[-1]
            splittedGA=self._mta_group_artifact.split(':')
            url="{scheme}://{netloc}/nexus/service/local/artifact/maven/resolve?g={group}&a={artifact}&v=LATEST&e=jar&r={repository}".format(scheme=o.scheme,netloc=o.netloc,group=splittedGA[0],artifact=splittedGA[1],repository=repoId)
            log.info( 'latest version of '+self._mta_group_artifact+' asked, searching for the latest version in nexus: ' + url )
            proxy_handler = urllib2.ProxyHandler({})
            opener = urllib2.build_opener(proxy_handler)
            opener.addheaders = [('Accept' , 'application/json')]
    
            # This time, rather than install the OpenerDirector, we use it directly:
            with contextlib.closing(opener.open(url)) as resp:
                jsonData=json.load(resp)['data']
                if 'baseVersion' in jsonData:
                    self._mta_version=jsonData['baseVersion'] # milestone mode
                elif 'version' in jsonData:
                    self._mta_version=jsonData['version'] # snapshot mode: no version field
                else:
                    raise XmakeException('"latest" defined as mta-version value, no version found in repo: "{}"'.format(repoId))

        return { 'default': ["{ga}:jar:{v}".format(ga=self._mta_group_artifact,v=self._mta_version),]}
    
    # list of tools needed to build target project
    def java_need_tools(self):
        # Don't need that for java tool because your using the spi.JavaBuildPlugin which ensure java is installed
        # def installJava(target_directory, version):
        #     # if root directory only contain 1 subdir, then the jdk java_home is this subdir otherwise the jdk_javahome is the install dir d
        #     installationDirectoryContent = os.listdir(target_directory)
        #     if len(installationDirectoryContent)>0:
        #         javaHomeToBeReturned=os.path.join(target_directory, installationDirectoryContent[0]);
        #         if os.path.isdir(javaHomeToBeReturned):
        #             return javaHomeToBeReturned

        #     return target_directory;

        # java_classifier = 'linux-x64' if os.name == 'posix' else 'windows-x64'

        def installMaven(target_directory, version):
            return os.path.join(target_directory,'apache-maven-'+version)

        def installNode(target_directory, version):
            return os.path.join(target_directory,'nodejs-'+version)

        def installMta(target_directory, version):
            return os.path.join(target_directory,'mta-'+version)

        return [
            {'toolid': self._maven_toolid, 'version': self._maven_version, 'type':'zip', 'classifier': 'bin', 'custom_installation': installMaven},
            {'toolid': self._node_toolid, 'version': self._node_version, 'type':'tar.gz', 'custom_installation': None},
        ]

    # Old fashion mechanism to download tools in custom plugin
    # We don't need that in an external plugin

    #def java_required_tool_versions(self):
	#return { 'maven': self._maven_version }
    #def variant_cosy_gav(self):
	#return None

    ###############################################################################
    #  XMAKE phase callbacks
    ###############################################################################
    def after_IMPORT(self, build_cfg):
        self.java_set_environment(True)
        # Setup maven
        self._setup()

        #If set-version option is on

        self._copy_src_dir_to(self._copied_src_dir)

        if build_cfg.get_next_version() is not None:
            raise XmakeException("version increment&management not implemented for MTA projects")
        elif build_cfg.base_version() == "NONE":
            initialize_src(self)

        #If get-version option is on
        if build_cfg.get_project_version() == True:

            status = self._check_project_version_compliance()
            if status[0] == False:
                raise XmakeException(status[1])
            else:

                stripped_version = self._remove_leading_zero(self.build_cfg.base_version())
                self.build_cfg.set_base_version(stripped_version)

                log.info('write project version {} in {}'.format(self.build_cfg.base_version(), self.build_cfg.project_version_file()))
                with open (self.build_cfg.project_version_file(), 'w') as f:
                    f.write(self.build_cfg.base_version())

    def after_BUILD(self, build_cfg):
        # Generate ads file before the export phase
        #if self.build_cfg.do_export():
    	if not self.build_cfg.skip_build() and not os.path.exists(build_cfg.export_script()):
            if "mtar" in self._mta_returned:
                log.info('building artifact deployer script (ads file)')
                self._generate_ads_file()
                log.info('artifact deployer script generated')
            else:
                log.warning('artifact deployer script (ads file) was not created, mtar filename missing')
	
    ###############################################################################
    #  XMAKE build phase & prepare deployment
    ###############################################################################
    def java_run(self):
        '''
            Callback invoked by xmake to execute the build phase
        '''
        
        if self._do_build:
            self._build()
        else:
            raise XmakeException('one of these profilings: "{}" is not supported'.format(','.join(self._profilings)))
	
    ###############################################################################
    #  Setup node files, environment variables
    ###############################################################################
    def _setup(self):
        '''
            Setup all the attributes of the class
        '''
        if self._maven_tool is None:
            self._maven_tool=MavenTool(self, self._maven_toolid, self._maven_version, self._mta_user_options)
                
        if self._npm_tool is None:
            self._npm_tool=NodeTool(self, self._node_toolid, self._node_version, self._mta_user_options)

        if self._grunt_tool is None:
            self._grunt_tool=GruntTool(self, self._node_toolid, self._node_version, self._mta_user_options)
            

    def _mta(self, args, fromdir = None, handler=None):
        '''
            Shortcut to invoke the maven executable
        '''

        if fromdir is None:
            fromdir = self._copied_src_dir

        mta_args = []
        mta_args.extend(["-jar", join(self.build_cfg.import_dir(),self._mta_group_artifact.split(':')[1]+"-"+self._mta_version+".jar")])
        mta_args.extend(args)
        log.info('from dir:', fromdir)
        log.info('invoking '+self._mta_group_artifact.split(':')[1]+': {}'.format(str(mta_args)))
        cwd=os.getcwd()
        try:
            os.chdir(fromdir)
            rc=self.java_log_execute(mta_args,handler=handler)
            if rc > 0:
                raise XmakeException('mta returned %s' % str(rc))
        finally:
            os.chdir(cwd)

    def _set_version_in_mta(self, version, fromdir = None):
        '''
            Set the given version to the project poms
        '''
        doc=None
        with open(join(self._build_cfg.component_dir(),"mta.yaml"), 'r') as f:
            doc = yaml.load(f)
        if doc:
            doc["version"]=version
            with open(join(self._build_cfg.component_dir(),"mta.yaml"), 'w') as f:
                yaml.dump(doc,f,default_flow_style=False)

    def _build(self):
        '''
            Build source files
        '''

        # generating unique output filename
        # Compile sources and install binaries in local repository
        mta_args = []
        self._mta_returned=dict()

        if self._mta_extension: 
            mta_args.extend(["--extension", self._mta_extension])
        self._mta_returned["mtar"]=join(self.build_cfg.gen_dir(),self.build_cfg.base_artifact()+".mtar")
        mta_args.extend(["--mtar", self._mta_returned["mtar"]])
                         
        mta_args.extend(["--build-target", self._mtar_build_target, "--show-data-dir", "build"])
        self._mta(mta_args)
        
              # builds bundle if bundle asked by user or if we are in staging mode
        if self._bundle or self.build_cfg.is_release() or self.build_cfg.get_staging_repoid_parameter():
            # create bundle file
            bundle_targz_file = join(self.build_cfg.gen_dir(), 'bundle.tar.gz')
            with tarfile.open(bundle_targz_file, 'w:gz') as tar:
                tar.add(self._mta_returned["mtar"], arcname=self.build_cfg.base_artifact()+".mtar")
            log.info('created tar of source and node nodules in {}'.format(bundle_targz_file))
        
        if isfile(self._ads): unlink(self._ads) 
        
    ###############################################################################
    #  Analyze build for deployment
    ###############################################################################
    def _generate_ads_file(self):        
        '''
            Create the artifact deployer script file
        '''        
        group_section_list = []        
        group_section_list.append('group "%s", {' %self.build_cfg.base_group())
        group_section_list.append('\tartifact "%s", {' %self.build_cfg.base_artifact())
                
        full_filname=self._mta_returned["mtar"]
        _, file_extension = os.path.splitext(full_filname)
        fileLine = '\t\t file "%s"' % full_filname.replace('\\', '/')
        fileLine = fileLine + ', extension:"%s"' % (file_extension[1:] if file_extension else "mtar")
        group_section_list.append(fileLine)

        if self._bundle or self.build_cfg.is_release() or self.build_cfg.get_staging_repoid_parameter():
            # create bundle file
            full_filname = join(self.build_cfg.gen_dir(), 'bundle.tar.gz')
            _, file_extension = os.path.splitext(full_filname)
            fileLine = '\t\t file "%s"' % full_filname.replace('\\', '/')
            fileLine = fileLine + ', extension:"tar.gz"'
            group_section_list.append(fileLine)
        
        group_section_list.append('}\n\t}')

        export_ads_template_file = join(os.path.dirname(os.path.realpath(__file__)), 'mtatemplate', 'export.ads')
        with open(export_ads_template_file, 'r') as f:
            export_ads = f.read()
        export_ads = Template(export_ads).substitute(groupList = '\n\t'.join(group_section_list))

        with open(self._ads, 'w') as f:
            f.write(export_ads)


    def _copy_src_dir_to(self, todir):
        '''
            Copy source files in another directory to avoid modifications in original source files.
        '''

        log.info('removing existing folder', todir)
        if os.path.exists(todir):
            OS_Utils.rm_dir(todir)

        os.mkdir(todir)

        log.info('copying files from', self.build_cfg.component_dir(), 'to', todir)

        for directory in os.listdir(self.build_cfg.component_dir()):
            if directory not in ['.xmake.cfg', 'gen', 'import', 'cfg', '.git', '.gitignore', 'target']:
                pathToCopy = join(self.build_cfg.component_dir(), directory)
                if path.isdir(pathToCopy):
                    shutil.copytree(pathToCopy, join(todir, directory))
                else:
                    shutil.copy2(pathToCopy, join(todir, directory))

    def _check_project_version_compliance(self):

            status = (True, "")
            if self.build_cfg.is_release() == 'direct-shipment':
                if not re.search(r"^[1-9]+\.\d+\.\d+$", self.build_cfg.base_version()):
                    err_message = 'ERR: project version %s does not respect the format for the direct shipment release. Version must have 3 digits and major greater than 0   ' % self.build_cfg.base_version()
                    status= (False,err_message)




             #############################
             # Three digit version format#
             #############################
            if self.build_cfg.is_release() == 'indirect-shipment':
                if not re.search(r"^\d+", self.build_cfg.base_version()):
                    err_message = 'ERR: project version %s does not respect the format for the indirect shipment release.' % self.build_cfg.base_version()
                    status= (False,err_message)


                is_compliant = False
                result = re.search(r"^(\d+\.\d+\.\d+)$", self.build_cfg.base_version())
                if result:
                    is_compliant = True

                else:
                    result = re.search(r"^(\d+\.\d+\.\d+)-(\d+)$", self.build_cfg.base_version())
                    if result:
                        version_digits = result.group(1)
                        self.build_cfg.set_base_version(version_digits)
                        is_compliant = True

#                     else:
#                         result = re.search(r"^(\d+\.\d+\.\d+)\.(\d+)$", self.build_cfg.base_version())
#                         if result:
#                             version_digits = result.group(1)
#                             self.build_cfg.set_base_version(version_digits)
#                             is_compliant = True
                    else:
                        result = re.search(r"^(\d+\.\d+\.\d+[-\.+])", self.build_cfg.base_version())
                        if result:
                            is_compliant = True
                            #############################
                            # Two digit version format  #
                            #############################
                        else:
                            result = re.search(r"^(\d+\.\d+)$", self.build_cfg.base_version())
                            if result:
                                self.build_cfg.set_base_version('{}.0'.format(self.build_cfg.base_version()))
                                is_compliant = True

                            else:
                                result = re.search(r"^(\d+\.\d+)[\.,-]([a-zA-Z]+[-\.]?\d*)$", self.build_cfg.base_version())
                                if result:
                                    version_digits = result.group(1)
                                    version_alphanumeric = result.group(2)
                                    self.build_cfg.set_base_version('{}.0-{}'.format(version_digits,version_alphanumeric))
                                    is_compliant = True

                                else:
                                    result = re.search(r"^(\d+\.\d+)-(\d+)$", self.build_cfg.base_version())
                                    if result:
                                        version_digits = result.group(1)
                                        self.build_cfg.set_base_version('{}.0'.format(version_digits))
                                        is_compliant = True
                                    else:
                                        result = re.search(r"^(\d+\.\d+)\.(0\d+)$", self.build_cfg.base_version())
                                        if result:
                                            version_digits = result.group(1)
                                            self.build_cfg.set_base_version('{}.0'.format(version_digits))
                                            is_compliant = True

                                            #############################
                                            # One digit version format  #
                                            #############################
                                        else:
                                            result = re.search(r"^([1-9]\d*)$", self.build_cfg.base_version())
                                            if result:
                                                self.build_cfg.set_base_version('{}.0.0'.format(self.build_cfg.base_version()))
                                                is_compliant = True
                                            else:
                                                result = re.search(r"^([1-9]\d*)[\.,-]([a-zA-Z]+[-\.]?\d*)$", self.build_cfg.base_version())
                                                if result:
                                                    version_digits = result.group(1)
                                                    version_alphanumeric = result.group(2)
                                                    self.build_cfg.set_base_version('{}.0.0-{}'.format(version_digits,version_alphanumeric))
                                                    is_compliant = True
                                                else:
                                                    result = re.search(r"^([1-9]\d*)\.(0\d+)$", self.build_cfg.base_version())
                                                    if result:
                                                        version_digits = result.group(1)
                                                        self.build_cfg.set_base_version('{}.0.0'.format(version_digits))
                                                        is_compliant = True
                                                    else:
                                                        result = re.search(r"^([1-9]\d*)-(\d+)$", self.build_cfg.base_version())
                                                        if result:
                                                            version_digits = result.group(1)
                                                            self.build_cfg.set_base_version('{}.0.0'.format(version_digits))
                                                            is_compliant = True



                if not is_compliant:
                    err_message = 'ERR: project version %s does not respect the format for the indirect shipment release.' % self.build_cfg.base_version()
                    status= (False,err_message)

            return status

    def _remove_leading_zero(self,given_version):

        result =  given_version.split("-")

        version_digits = result[0]
        version_suffix = result[1:]

        version_tab = version_digits.split(".")
        stripped_version_tab = []
        for elem in version_tab:
            if elem.isdigit():
                elem = str(int(elem))
            stripped_version_tab.append(elem)

        stripped_version = '.'.join(stripped_version_tab)
        if len(version_suffix) > 0:
            stripped_version = stripped_version + '-' + '-'.join(version_suffix)

        return stripped_version


    
