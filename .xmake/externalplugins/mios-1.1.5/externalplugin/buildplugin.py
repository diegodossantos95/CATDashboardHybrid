'''
Created on 27.03.2015

@author: I050906, I051432, I079877, I051375
'''
import log
import os
import xml.etree.ElementTree as ET
import inst
import re
import shlex
import urlparse
import subprocess
import urllib
import shutil
from artifact import Artifact
from string import Template
from ExternalTools import OS_Utils
from os import path
from os.path import join
from xmake_exceptions import XmakeException
#from spi import JavaBuildPlugin
import spi
import shutil
import json
import sys
import glob

COMMONREPO='Common'
NPMREPO='NPM'
DOCKERREPO='Docker'
HTML_TEMPLATE = "<html><head><meta http-equiv=\"refresh\" content=\"0; URL=$LOCATION\"> <body>You will be redirected within the next few seconds.<br /> In case this does not work click <a href=\"$LOCATION\">here</a></body></html>"

class BuildPlugin(spi.JavaBuildPlugin):
    '''
        Xmake maven plugin class that provides the ability to build maven project
    '''
    RESERVED_OPTIONS = ('validate', 'compile', 'test', 'package', 'integration-test', 'verify', 'install', 'deploy')

    ###############################################################################
    #  PLUGIN initialization
    ###############################################################################
    def __init__(self, build_cfg):
        spi.JavaBuildPlugin.__init__(self, build_cfg)
        self._maven_version = '3.0.5'
        self._maven_group_artifact = 'org.apache.maven:apache-maven'
        self._fortify_plugin_version = '1.7.0'
        self._tycho_set_version_version = '0.23.1'
        self._m2_home = ''
        self._maven_cmd = ''
        self._maven_settings_noproxy = None
        self._maven_settings_xml_file = ''
        self._maven_jvm_options = []
	self._maven_profiles_sent = ''
        self._maven_user_options = []
        self._maven_depencies = []
        self._maven_build_dependencies_file = ''
        self._maven_repository_dir = ''
        self._maven_installed_files = []
        self._localDeploymentPath = join(self.build_cfg.temp_dir(), 'localDeployment')
        self._ads = join(self.build_cfg.temp_dir(), 'export.ads')
        self._copied_src_dir = join(self.build_cfg.temp_dir(), 'src')
        self._relative_pom_path = self.build_cfg.alternate_path()

        self._profilings = self.build_cfg.profilings()
        if self._profilings is None:
            self._do_build = True
            self._do_fortify_build = False
        elif len(self._profilings)==1 and ('FORTIFY' in self._profilings or 'fortify' in self._profilings):
            self._do_build = False
            self._do_fortify_build = True
            self.build_cfg.set_custom_deploy(True)
        else:
            self._do_build = False
            self._do_fortify_build = False

        # Take in account arguments after the --
        # All these arguments will be passed to the mvn command
        if self.build_cfg.build_args():
            for arg in self.build_cfg.build_args():
                log.info( '  using custom option ' + arg)
                if arg not in BuildPlugin.RESERVED_OPTIONS:
                    self._maven_user_options.append(arg)
                    if(arg.startswith('-Pcentral')):
			self._maven_profiles_sent=arg
			log.debug('Have set the profile sent to',self._maven_profiles_sent)
                else:
                    log.warning('  ignoring custom option {}. Only xmake can manage this option.'.format(arg))

        self.build_cfg.set_export_script(self._ads)

    def java_set_option(self,o,v):
        if o == 'maven-version' or o == 'version':
            log.info( '\tusing maven version ' + v)
            self._maven_version = v
        # enhances this plugin to be able to specify the group:artifact of maven in config .xmake.cfg
        elif o == 'maven-group-artifact':
            log.info( '\tusing maven ' + v)
            self._maven_group_artifact = v
        elif o == 'fortify-plugin-version':
            log.info( '\tusing fortify-plugin version ' + v)
            self._fortify_plugin_version = v
        elif o == 'noproxy':
            self._maven_settings_noproxy = v and v.lower() in ('true', 'y', 'yes')
            if self._maven_settings_noproxy:
                log.info( '\tusing noproxy={}. Proxy setting will be removed from settings.xml'.format(self._maven_settings_noproxy))
            else:
                log.info( '\tusing noproxy={}. Proxy setting will be kept in settings.xml'.format(self._maven_settings_noproxy))
        elif o =='options':
            values = v.split(',')
            for value in values:
                log.info( '\tusing custom option ' + value)
                if value not in BuildPlugin.RESERVED_OPTIONS:
                    self._maven_user_options.append(value)
                else:
                    log.warning('\tignoring custom option {}. Only xmake can manage this option.'.format(value))
        elif o=='tycho-setversion-version':
            log.info( '\tusing tycho plugins version ' + v + ' for setting pom.xml(s) version(s)')
            self._tycho_set_version_version=v;
        else:
            if o is not None: v="%s=%s"%(o,v) # does not correspond to one of the option above remangle it as originally splitted by JavaBuildPlugin if it was containing an equal char
            log.info( '\tusing custom option ' + v)
            self._maven_user_options.append(v)

    # list of tools needed to build target project
    def need_tools(self):
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

        return [
            # {'toolid': self._java_group_artifact, 'version': self._java_version, 'type':'tar.gz', 'classifier': java_classifier, 'custom_installation': installJava},
            {'toolid': self._maven_group_artifact, 'version': self._maven_version, 'type':'zip', 'classifier': 'bin', 'custom_installation': installMaven}
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
            self._set_version_in_pom(build_cfg.get_next_version(), build_cfg.component_dir())
            # Always copy src see BESTL-8640 Related to Cloud Foundry deployment
            #self._copy_src_dir_to(self._copied_src_dir)

        elif build_cfg.base_version() == "NONE":
            # Always copy src see BESTL-8640 Related to Cloud Foundry deployment
            #self._copy_src_dir_to(self._copied_src_dir)
            self._set_version_from_effective_pom()


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


	if not os.path.exists(build_cfg.export_script()):
            log.info('building artifact deployer script (ads file)')
            self._generate_ads_file()
            log.info('artifact deployer script generated')
	
    def after_DEPLOY(self, build_cfg):
	# MIOS
	#self.create_OTA_temp()
	if (os.path.exists(self.build_cfg.deployment_info_log())):
	    log.debug('deployment info log found. Creating last successful artifacts') 
	    self.createSuccesfulArtifactFolder()
	    
	else:
	    log.debug('No deployment Info log found')
        # custom deployment
	
        if self._do_fortify_build and self.build_cfg.do_deploy():
            self._fortifyDeploy()

    ###############################################################################
    #  XMAKE build phase & prepare deployment
    ###############################################################################
    def java_run(self):
        '''
            Callback invoked by xmake to execute the build phase
        '''

        self._clean_if_requested()
        #Function to unlock keygen for mios
        self.unlock_ios_keychain()

        #export repo mios
        #self.build_cfg._export_repos={ COMMONREPO: 'http://nexus.wdf.sap.corp:8081/nexus/content/repositories/deploy.snapshots/',
               #}
        #:log.info("EXPORT_REPO:",self.build_cfg._export_repos)

        if self._do_build:
            self._build()
        elif self._do_fortify_build:
            self._fortifyBuild()
        else:
            raise XmakeException('one of these profilings: "{}" is not supported'.format(','.join(self._profilings)))
	
	#self.generateURLfromdf()#Temporary
    ###############################################################################
    #  Setup maven files, environment variables
    ###############################################################################
    def _setup(self):
        '''
            Setup all the attributes of the class
        '''

        self._m2_home = self.build_cfg.tools()['maven'][self._maven_version]
        self._maven_cmd = self._find_maven_executable()
        self._maven_settings_xml_file = join(self.build_cfg.temp_dir(), 'settings.xml')
        self._maven_jvm_options = ['-Djavax.net.ssl.trustStore='+join('miostemplate', 'keystore'),
                                   '-Dmaven.wagon.http.ssl.insecure=true', # Use keystore because these two VM options have no effect on maven...
                                   '-Dmaven.wagon.http.ssl.allowall=true'] # Also tried to use MAVEN_OPTS but no effect as well
        self._maven_build_dependencies_file = join(self.build_cfg.temp_dir(), "dependencies")
        self._maven_repository_dir = join(self.build_cfg.temp_dir(), 'repository')
        self._setup_settings_xml()
        self.java_exec_env.env['VERSION'] = self.build_cfg.base_version()
        self.java_exec_env.env['REPOSITORY'] = self._maven_repository_dir


    def _setup_settings_xml(self):
        '''
            Build a custom settings.xml file from a template located in [plugin_dir]miostemplate/settings.xml
            Mainly two fields are customized:
             - localRepository
             - mirrors/mirror/url
            This new file is saved into [component_dir]/gen/tmp/settings.xml
        '''

        # Add xml namespaces
        ET.register_namespace('', 'http://maven.apache.org/SETTINGS/1.0.0')
        ET.register_namespace('xsi', "http://www.w3.org/2001/XMLSchema-instance")
        ET.register_namespace('xsi:schemaLocation', 'http://maven.apache.org/SETTINGS/1.0.0 http://maven.apache.org/xsd/settings-1.0.0.xsd')

        # Parse template/settings.xml
        templateSettingsXmlFile = join(os.path.dirname(os.path.realpath(__file__)),'miostemplate', 'settings.xml')
        xmlSettingsContent = ''
        with open(templateSettingsXmlFile, 'r') as f:
            xmlSettingsContent = f.read()


        tree = ET.fromstring(xmlSettingsContent)
        if tree is None:
            raise XmakeException( 'cannot generate specific settings.xml for maven')

        #Search fileds to update
        namespace = "{http://maven.apache.org/SETTINGS/1.0.0}"
        localRepository = tree.find('./{}localRepository'.format(namespace))
        mirrorUrl = tree.find('./{0}mirrors/{0}mirror[{0}id="mirror1"]/{0}url'.format(namespace))
        repositoryUrl = tree.find('./{0}profiles/{0}profile[{0}id="cutomized.repo"]/{0}repositories/{0}repository[{0}id="central"]/{0}url'.format(namespace))
        sonarproperties = tree.find('./{0}profiles/{0}profile[{0}id="sonar"]/{0}properties'.format(namespace))
        sonarjdbcurl = sonarproperties.find('{0}sonar.jdbc.url'.format(namespace))
        sonarjdbcdriver = sonarproperties.find('{0}sonar.jdbc.driver'.format(namespace))
        sonarjdbcusername = sonarproperties.find('{0}sonar.jdbc.username'.format(namespace))
        sonarjdbcpassword = sonarproperties.find('{0}sonar.jdbc.password'.format(namespace))
        sonarhosturl = sonarproperties.find('{0}sonar.host.url'.format(namespace))

        if localRepository is None and mirrorUrl is None:
            raise XmakeException('cannot generate specific settings.xml for maven')

        # Add specific fields
        localRepository.text = self._maven_repository_dir
        mirrorUrl.text = self.build_cfg.import_repos()[0]
        repositoryUrl.text = self.build_cfg.import_repos()[0]
        if self.build_cfg.is_release() is None:
            pluginrepositoryUrl = tree.find('./{0}profiles/{0}profile[{0}id="cutomized.repo"]/{0}pluginRepositories/{0}pluginRepository[{0}id="central"]/{0}url'.format(namespace))
            pluginrepositoryUrl.text = self.build_cfg.import_repos()[0]

        # sonar properties
        jdbcurl = os.getenv('SONAR_JDBC_URL') #jdbc:mysql://ldisonarci.wdf.sap.corp:3306/sonar?useUnicode=true&characterEncoding=utf8
        jdbcdriver = os.getenv('SONAR_JDBC_DRIVER') #com.mysql.jdbc.Driver
        jdbcusername = os.getenv('SONAR_JDBC_USERNAME') #sonar
        jdbcpassword = os.getenv('SONAR_JDBC_PASSWORD') #sonar
        hosturl = os.getenv('SONAR_HOST_URL') #http://ldisonarci.wdf.sap.corp:8080/sonar

        logWarnings = []

        # Check server utl is set
        if jdbcurl is None:
            logWarnings.append('jdbc url is not set for sonar. Please set env SONAR_JDBC_URL');
        if jdbcdriver is None:
            logWarnings.append('jdbc driver is not set for sonar. Please set env SONAR_JDBC_DRIVER')
        if jdbcusername is None:
            logWarnings.append('jdbc username is not set for sonar. Please set env SONAR_JDBC_USERNAME')
        if jdbcpassword is None:
            logWarnings.append('jdbc password is not set for sona. Please set env SONAR_JDBC_PASSWORD')
        if hosturl is None:
            logWarnings.append('sonar host url is not set. Please set env SONAR_HOST_URL')

        if len(logWarnings)>0:
            for logWarning in logWarnings:
                log.warning(logWarning, log.INFRA)
        else:
            sonarjdbcurl.text = jdbcurl
            sonarjdbcdriver.text = jdbcdriver
            sonarjdbcusername.text = jdbcusername
            sonarjdbcpassword.text = jdbcpassword
            sonarhosturl.text = hosturl

        # Write settings.xml in component/tmp directory
        log.info( 'write maven settings in ' + self._maven_settings_xml_file)
        #tree.write(self._maven_settings_xml_file)
        with open(self._maven_settings_xml_file,'w') as f:
            f.write(ET.tostring(tree))

    def _find_maven_executable(self):
        '''
            Find the mvn command path according to the operating system
        '''

        if OS_Utils.is_UNIX():
            path = join(self._m2_home,'bin','mvn')
        else:
            path = join(self._m2_home,'bin','mvn.cmd')
            if not os.path.isfile(path):
                path = join(self._m2_home,'bin','mvn.bat')
        return path

    def _mvn(self, args, fromdir = None):
        '''
            Shortcut to invoke the maven executable
        '''

        if fromdir is None:
            fromdir = self._copied_src_dir

        maven_args = [self._maven_cmd]
        maven_args.extend(args)
        if self._relative_pom_path is not None:
            maven_args.extend(['-f', join(self._relative_pom_path,"pom.xml")]) # use alternate pom file given by project portal
        #maven_args.append("-B") # in non-interactive (batch)
        maven_args.append("-e") # Produce execution error messages
        maven_args.extend(['-settings', self._maven_settings_xml_file])
        maven_args.extend(self._maven_jvm_options)

        # manage ldi variables
        if self.build_cfg.is_release() == 'direct-shipment' or self.build_cfg.is_release() == 'indirect-shipment':
            maven_args.append('-Dldi.releaseBuild=true')
            maven_args.append('-Dldi.releaseType=customer')
        elif self.build_cfg.is_release() == 'milestone':
            maven_args.append('-Dldi.releaseBuild=true')
            maven_args.append('-Dldi.releaseType=milestone')


        log.info('from dir:', fromdir)
        log.info('invoking maven: {}'.format(' '.join(self._hide_password_in_maven_args_for_log(maven_args))))
        cwd=os.getcwd()
        try:
            os.chdir(fromdir)
            rc=self.java_exec_env.log_execute(maven_args)
            if rc > 0:
                raise XmakeException('maven returned %s' % str(rc))
        finally:
            os.chdir(cwd)

    def _set_version_from_effective_pom(self):
        '''
            Compute maven effective pom to find the version of the project
        '''

        maven_args = ['help:effective-pom', '-Doutput={}{}effective-pom.xml'.format(self.build_cfg.temp_dir(), os.sep)]
	if('-Pcentral' in self._maven_profiles_sent):
		log.debug('There are profiles sent via user options, so we are enabling them even in effetive pom building')
		maven_args.append(self._maven_profiles_sent)
                #log.debug('Ganesh_mvn_args',maven_args)
        self._mvn(maven_args)

        f = join(self.build_cfg.temp_dir(),"effective-pom.xml")
        pom = ET.parse(f)
        root = pom.getroot()
        if root.tag is None:
            raise XmakeException('version entry not found in effective-pom xml')

        namespace = "{http://maven.apache.org/POM/4.0.0}"
        group = None
        artifact = None
        version = None
        tag = root.tag.split("}",1)[-1]
        if tag == "project":
            group = pom.find('{}groupId'.format(namespace))
            artifact = pom.find('{}artifactId'.format(namespace))
            version = pom.find('{}version'.format(namespace))
        elif tag == "projects":
            group = pom.find('{0}project/{0}groupId'.format(namespace))
            artifact = pom.find('{0}project/{0}artifactId'.format(namespace))
            version = pom.find('{0}project/{0}version'.format(namespace))

        if not (version is None or group is None or artifact is None):

            strippedVersion = re.sub(r'\-(?i)(SNAPSHOT|RELEASE|MILESTONE)$', '', version.text)
            log.info('version after cleaning redundant suffixe: ' + strippedVersion)
            self.build_cfg.set_base_version(strippedVersion)
            self.build_cfg.set_version(strippedVersion)
            self.build_cfg.set_base_group(group.text)
            self.build_cfg.set_base_artifact(artifact.text)

        else:
            raise XmakeException('group, artifact or version entry not found in effective-pom xml')

    def _set_version_in_pom(self, version, fromdir = None):
        '''
            Set the given version to the project poms
        '''

        maven_args = ['org.eclipse.tycho:tycho-versions-plugin:{}:set-version'.format(self._tycho_set_version_version), '-DnewVersion={}'.format(version), '-Dldi.tycho-parent.tycho-version={}'.format(self._tycho_set_version_version)]
        self._mvn(maven_args, fromdir = fromdir)

    def _run_metadata_quality_check(self, qualtity_check_config):
        '''
            During the release build, the metadata-quality-report plugin is used to perform certain checks on the project
        '''
        maven_args = []
        maven_args.append('com.sap.ldi:metadata-quality-report:check')
        maven_args.append('-Dmetadata-quality-report.dependencies=com.sap.ldi.releasetools:mqr-config:2.1.0')


        maven_args.append(qualtity_check_config)
        self._mvn(maven_args)

    def _run_metadata_quality_check_mios(self, qualtity_check_config):
        '''
            During CI, VOTTER and OD builds we check Metada check based on the jobbase xml in MIOS
        '''
        maven_args = []
	#log.info('Ganesh',qualtity_check_config)
	for argOfMvn in qualtity_check_config:
		maven_args.append(argOfMvn)
		#log.info('Ganesh_argOfMvn',argOfMvn)
	#log.info('FullMavenArgs',maven_args)
        self._mvn(maven_args)

    def _build(self):
        '''
            Build source files
        '''
        # Maven phases:
        #  validate - validate the project is correct and all necessary information is available
        #  compile - compile the source code of the project
        #  test - test the compiled source code using a suitable unit testing framework. These tests should not require the code be packaged or deployed
        #  package - take the compiled code and package it in its distributable format, such as a JAR.
        #  integration-test - process and deploy the package if necessary into an environment where integration tests can be run
        #  verify - run any checks to verify the package is valid and meets quality criteria
        #  install - install the package into the local repository, for use as a dependency in other projects locally
        #  deploy - done in an integration or release environment, copies the final package to the remote repository for sharing with other developers and projects.

        # Metadata quality check only for release or milestone build
        # See details of checks in https://wiki.wdf.sap.corp/wiki/display/LeanDI/Release+Build+Details#ReleaseBuildDetails-VersionUpdates

	# Run the metada quality check for mios type of builds
        log.debug('Start of Metada quality check specific to MiOS')
	if self.build_cfg.build_args():
            for arg in self.build_cfg.build_args():	
		#log.info('Ganesh:',arg)
		if arg.find('metadata-quality-report.configuration') >= 0:
			#log.info('Ganesh:Matchfound')
			self._run_metadata_quality_check_mios(self._maven_user_options)
			log.debug('End of checking the metada arg')
			log.debug('Exiting the build phase after Metada quality check')
			return True
        
	if self.build_cfg.is_release() == 'direct-shipment' or self.build_cfg.is_release() == 'indirect-shipment':
            # For a customer release build use quality-check-config-customer.xml
            self._run_metadata_quality_check('-Dmetadata-quality-report.configuration=quality-check-config-customer.xml')
        elif self.build_cfg.is_release() == 'milestone':
            # For a milestone build use quality-check-config-milestone.xml
            self._set_version_in_pom(self.build_cfg.base_version())
            self._run_metadata_quality_check('-Dmetadata-quality-report.configuration=quality-check-config-milestone.xml')

        # Compile sources and install binaries in local repository
        maven_args = []

        # Manage clean phase
        if self.build_cfg.do_clean():
            maven_args.append('clean')

        # prepare filesystem for local deployment
        if os.path.exists(self._localDeploymentPath):
            OS_Utils.rm_dir(self._localDeploymentPath)
        localDeploymentUrl = urlparse.urljoin('file:', urllib.pathname2url(self._localDeploymentPath))
	log.info('debug21',localDeploymentUrl)

        # Go until install phase to install package locally and
        # to be able to use it as dependency in other local projects
        maven_args.append('deploy')
        maven_args.append('-DaltDeploymentRepository=local::default::{}'.format(localDeploymentUrl))
        maven_args.append('-DuniqueVersion=false')

        # add options for signing
        maven_args.extend(self._maven_jarsigner_plugin_options(self.build_cfg.is_release()))

        if self.build_cfg.skip_test():
            maven_args.append('-Dmaven.test.skip=true')

        # add user options
        maven_args.extend(shlex.split(" ".join(self._maven_user_options)))

        # call mvn command
        self._mvn(maven_args)

        # Store build dependencies
        log.info('building dependencies')
        self._store_build_dependencies()

    def _maven_jarsigner_plugin_options(self, releaseBuild):
        '''
            Signing with Lean DI (during a release build) ensures that build results are signed with valid certificates.
            released artifacts are signed with official SAP certificate
            locally build artifacts are signed with a self-signed certificate
            For signing during the release build, artifacts must be registered at final assembly.
        '''
        options = []

        # Read option values from os environment
        serverurl = os.getenv('SIGNING_PROXY_URL') #https://signproxy.wdf.sap.corp:28443/sign
        keystore = os.getenv('SIGNING_KEYSTORE_PATH')
        keystorepass = os.getenv('SIGNING_KEYSTORE_PASSWORD')
        truststore = os.getenv('SIGNING_TRUSTSTORE_PATH')
        truststorepass = os.getenv('SIGNING_TRUSTSTORE_PASSWORD')

        logWarnings = []

        # Check server utl is set
        if serverurl is None:
            logWarnings.append('signing server url not set. Please set env SIGNING_PROXY_URL');
        elif not serverurl.startswith('http://') and not serverurl.startswith('https://'):
            logWarnings.append('bad signing server url waiting for http/https url: {}'.format(serverurl))

        # Check keystore exists
        if keystore is None:
            logWarnings.append('signing keystore path not set. Please set env SIGNING_KEYSTORE_PATH')
        elif not os.path.exists(keystore):
            logWarnings.append('signing keystore path does not exist {}'.format(keystore))
        elif os.path.isdir(keystore):
            logWarnings.append('signing keystore path does not point to a file {}'.format(keystore))

        if keystorepass is None:
            logWarnings.append('signing keystore password not set. Please set env SIGNING_KEYSTORE_PASSWORD')

         # Check truststore exists
        if truststore is None:
            logWarnings.append('signing truststore path not set. Please set SIGNING_TRUSTSTORE_PATH')
        elif not os.path.exists(truststore):
            logWarnings.append('signing truststore path does not exist {}'.format(truststore))
        elif os.path.isdir(truststore):
            logWarnings.append('signing truststore path does not point to a file {}'.format(truststore))

        if truststorepass is None:
            logWarnings.append('signing truststore password not set. Please set SIGNING_TRUSTSTORE_PASSWORD')

        if len(logWarnings)>0:
            for logWarning in logWarnings:
                log.warning(logWarning, log.INFRA)
            log.warning('real singning parameters not set')
            return options

        if releaseBuild:
            log.info('real jar signing activated')
        options.append('-Dcodesign.sap.realcodesigning={}'.format('true' if releaseBuild else 'false'))
        options.append('-Dcodesign.sap.server.url={}'.format(serverurl))
        options.append('-Dcodesign.sap.ssl.keystore={}'.format(keystore))
        options.append('-Dcodesign.sap.ssl.keystore.pass={}'.format(keystorepass))
        options.append('-Dcodesign.sap.ssl.truststore={}'.format(truststore))
        options.append('-Dcodesign.sap.ssl.truststore.pass={}'.format(truststorepass))
        return options

    def _fortifyBuild(self):
        '''
            Build source files with fortify
        '''

        log.info('fortify translate and scan')

        # Compile sources and install binaries in local repository
        base_maven_args = []
        base_maven_args.append('-Dmaven.test.skip=true')

        # add user options
        base_maven_args.extend(shlex.split(" ".join(self._maven_user_options)))

        # fortify translate
        translate_args = []
        if self.build_cfg.do_clean():
            translate_args.append('clean')
        translate_args.append('install')
        translate_args.append('com.sap.ldi:fortify-plugin:{}:translate'.format(self._fortify_plugin_version))
        translate_args.extend(base_maven_args)
        self._mvn(translate_args)

        # fortify scan
        scan_args = []
        scan_args.append('com.sap.ldi:fortify-plugin:{}:scan'.format(self._fortify_plugin_version))
        scan_args.extend(base_maven_args)
        self._mvn(scan_args)

    def _fortifyDeploy(self):
        '''
            Deploy fortify result in corporate fortify server
        '''

        log.info('fortify upload')

        # Read option values from os environment
        serverurl = os.getenv('FORTIFY_F360_URL') #https://fortify1.wdf.sap.corp/ssc
        token = os.getenv('FORTIFY_F360_AUTH_TOKEN')

        logErrors = []
        if serverurl is None:
            logErrors.append('fortify server url not set. Please set env FORTIFY_F360_URL');
        elif not serverurl.startswith('http://') and not serverurl.startswith('https://'):
            logErrors.append('bad fortify server url waiting for http/https url: {}'.format(serverurl))

        if token is None:
            logErrors.append('fortify token not set. Please set env FORTIFY_F360_AUTH_TOKEN')

        if len(logErrors)>0:
            for error in logErrors:
                log.error(error, log.INFRA)
            raise XmakeException('fortify results upload fails')

        # fortify deploy
        maven_args = []
        maven_args.append('com.sap.ldi:fortify-plugin:{}:upload'.format(self._fortify_plugin_version))
        maven_args.append('-Dldi.fortify.f360.url={}'.format(serverurl))
        maven_args.append('-Dldi.fortify.f360.authToken={}'.format(token))
        maven_args.append('-Dldi.fortify.f360.projectVersion={}'.format(self.build_cfg.base_version().split('.')[0]))
        maven_args.extend(shlex.split(" ".join(self._maven_user_options)))
        self._mvn(maven_args)

    ###############################################################################
    #  Analyze and store build dependencies
    ###############################################################################

    def _store_build_dependencies(self):
        '''
            Store build dependencies in this format [group:artifact:version:type::classifier]
            ie: log4j-1.2.12-debug.jar --> log4j:log4j:1.2.12:jar::debug
            The file will be saved in [component_dir]/gen/tmp/dependencies
        '''
        artifacts = Artifact.gather_artifacts(self._maven_repository_dir)
        lines = []
        for key in artifacts:
            values = artifacts[key]
            for artifact in values:

                str_key = ":".join([key,artifact.extension])
                if artifact.classifier:
                    str_key = "::".join([str_key, artifact.classifier])
                lines.append(str_key)

        with open(self._maven_build_dependencies_file, 'w') as f:
            f.writelines(["%s\n" % line for line in lines])

        self.build_cfg.add_metadata_file(self._maven_build_dependencies_file)
        log.info('found '+ `len(lines)` +' dependencies')

    ###############################################################################
    #  Analyze build for deployment
    ###############################################################################
    def _generate_ads_file(self):
        '''
            Create the artifact deployer script file
        '''
        # Retrieve artifacts from local deployment repo
        artifacts = Artifact.gather_artifacts(self._localDeploymentPath)

        group_section_list = []
        lines = []
        for key in artifacts:
            values = artifacts[key]
            gav = key.split(':')
            group = gav[0]
            aid= gav[1]
            group_section_list.append('group "%s", {' %group)
            group_section_list.append('\tartifact "%s", {' %aid)

            for artifactObj in values:
                log.info("artifact to deploy "+ artifactObj.path)
                fileLine = '\t\t file "%s"' % artifactObj.path.replace('\\', '/')
                if not artifactObj.classifier == "":
                    fileLine = fileLine + ', classifier:"%s"' % (artifactObj.classifier)
                if not artifactObj.extension == "":
                    fileLine = fileLine + ', extension:"%s"' % (artifactObj.extension)
                group_section_list.append(fileLine)

                # Removed this restriction according to the new wanted behaviour see BESTL-8564
                # # Check that all submodules POMs have the same version as the main (Reactor) POM
                # project_version = self.build_cfg.version()
                # strippedVersion = re.sub(r'\-(?i)(SNAPSHOT|RELEASE|MILESTONE)$', '', artifactObj.version)
                # if strippedVersion != project_version:
                #     errorMessage = 'the following sub module POM %s:%s:%s has different version from the main POM  %s' % (artifactObj.gid, artifactObj.aid,artifactObj.version,project_version)
                #     errorMessage= errorMessage + ' All sub modules POM must have the same version as the main POM '
                #     raise XmakeException( errorMessage)

            group_section_list.append('}\n\t}')

        export_ads_template_file = join(os.path.dirname(os.path.realpath(__file__)), 'miostemplate', 'export.ads')
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

    def _hide_password_in_maven_args_for_log(self, maven_args):
        '''
            Hide password in logs
        '''

        argsToHide=['-Dcodesign.sap.ssl.keystore.pass=',
                    '-Dcodesign.sap.ssl.truststore.pass=',
                    '-Dldi.fortify.f360.authToken=']

        maven_args_to_log = []
        # loop on maven args
        for arg in maven_args:
            if arg:
                found = False
                # loop on args to hide
                for argToHide in argsToHide:
                    if arg.startswith(argToHide):
                        found = True
                        maven_args_to_log.append(arg.split('=')[0] + '=*******')
                        break

                if not found:
                    maven_args_to_log.append(arg)

        return maven_args_to_log

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
        print "version_suffix = {}".format(version_suffix)

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

    def unlock_ios_keychain(self):
        log.info('Preparing Prerequisite for IOS app creation...')
        prodpass_path = self.build_cfg.tools().prodpassaccess()
        prodpass_cmd_out = '`' + prodpass_path +' --credentials-file ' + os.environ['HOME'] + '/.prodpassaccess/credentials.properties --master-file ' + os.environ['HOME'] +'/.prodpassaccess/master.xml get unlock-keychain password`'
        print prodpass_cmd_out
        keychain_file = os.environ['HOME'] + '/Library/Keychains/login.keychain'
        log.info('Unlocking iOS keychain...')
        unlockcommand = 'security unlock-keychain -p ' + prodpass_cmd_out + ' ' + keychain_file
        os.system(unlockcommand)
        unlock_return_code = subprocess.call([
            'security', 'unlock-keychain', '-p', prodpass_cmd_out , keychain_file
        ])
        if unlock_return_code == 0:
            log.info('SUCCESS - iOS key chain unlock successfully done')
        else:
            log.warning('FAILURE - iOS app signing Unsuccessfully')

    def create_localDeploymentFolder(self):
	log.info('Creating localDeployment folder outside gen for Jenkins server plugin')
	shutil.copytree(self._localDeploymentPath, 'artifactRedirect')

    def createSuccesfulArtifactFolder(self):
	j_file = self.build_cfg.deployment_info_log()
	log.debug('Found deployment_info_log file',j_file)
        sepratorForGA = '_abcz_'
        dictGA = {}
        dictURL = {}
        log.debug('Info:Parsing the json file',j_file)
        with open(j_file) as f:
            j_obj = json.load(f)
            urlValues = j_obj['deploymentInfos']
            for rs in urlValues:
                urlFromJson = rs['URL']
                j_groupId = rs['artifact']['groupId']
                j_artifactId = rs['artifact']['artifactId']
                keyForGA = j_groupId + sepratorForGA + j_artifactId
                dictGA[keyForGA] = 0
                dictURL[urlFromJson] = keyForGA
        
        log.debug('Info: List of GroupId and ArtifactIds seprated by ', sepratorForGA)
	
	for keyURL in dictURL.iterkeys():
		artifact_groupId = dictURL[keyURL].split(sepratorForGA)[0]
		artifact_artifactId = dictURL[keyURL].split(sepratorForGA)[1]
		artifactFolderPath = self.create_artifactREdirectFolderStructure(artifact_groupId, artifact_artifactId)

		htmlurl = HTML_TEMPLATE.replace("$LOCATION",keyURL)
		artifactFileFullName = keyURL.rpartition('/')[2]
		artifactName = self.getRedirectHtmlFilename(artifactFileFullName, artifact_artifactId)
		self.createHTMLFileforArtifacts(artifactName, artifactFolderPath, htmlurl)

    def getNthIndexFromBack(self, string, searchString, countFromBack):
	if (countFromBack <= 0):
		return -1
	idx =len(string)
	for i in range(0, countFromBack):
		idx=string[0:idx].rfind(searchString)
	if idx <= 0:
		return idx
	return idx

    def getRedirectHtmlFilename(self, artifactFileName, artifactId):
	OTA_CLASSIFIER_APPENDIX = '-ota'
	OTA_HTML_FILE_APPENDIX = 'htm'
	searchval= '-'
	nthElement=0
	joindata=OTA_CLASSIFIER_APPENDIX+'.'+OTA_HTML_FILE_APPENDIX

	if artifactFileName.endswith(joindata):
		nthElement=3
	elif artifactFileName.endswith("-AppStoreMetaData.zip"):
		nthElement = 1
	elif (artifactFileName.endswith("-app.dSYM.zip")):
		nthElement = 3
	elif (artifactFileName.endswith("-app.zip")):
		nthElement = 3
	elif (artifactFileName.endswith(".ipa")):
		nthElement = 2
	elif (artifactFileName.endswith("versions.xml")):
		nthElement = 1
	elif (artifactFileName.endswith(".pom")):
		nthElement = 1
		searchval = "."
	elif (artifactFileName.endswith("-fat-binary.a")):
		nthElement = 3
	elif (artifactFileName.endswith(".a")):
		nthElement = 2
	elif (artifactFileName.endswith(".headers.tar")):
		nthElement= 2
	elif (artifactFileName.endswith(".tar")):
		nthElement= 1
		searchval ='.'
	idx = self.getNthIndexFromBack(artifactFileName,searchval,nthElement)
	if idx >= 0 :
		name = artifactId + artifactFileName[idx:]
		if not name.endswith(".htm"):
			name = name + ".htm"
		return name
	return artifactId + "-" + artifactFileName + ".htm"

    def createHTMLFileforArtifacts(self, artifactName, artifact_dir, htmlurl):
	filename = os.path.join(artifact_dir, artifactName)
	HTML_FILE = open(filename,'w')
	HTML_FILE.write(htmlurl)
	HTML_FILE.close()

    def create_artifactREdirectFolderStructure(self, artifact_groupId, artifact_artifactId):
	if os.path.exists(self.build_cfg.gen_dir()):
		artifact_dir = r"artifactsRedirect/artifacts/"
		artifactFolder = os.path.join(self.build_cfg.gen_dir(), artifact_dir, artifact_groupId, artifact_artifactId)
		if not os.path.exists(artifactFolder):
			os.makedirs(artifactFolder)
		return artifactFolder

    def create_OTA_temp(self):
	if os.path.exists(self.build_cfg.gen_dir()):
		log.info("level1")
		artifact_dir = r"artifactsRedirect/artifacts/gav_ota/"
		artifactFolder = os.path.join(self.build_cfg.gen_dir(), artifact_dir)
		log.info("path; ",artifactFolder)
                if not os.path.exists(artifactFolder):
			log.info("level2")
                        os.makedirs(artifactFolder)

		os.chdir(self._localDeploymentPath)
		log.info('level 2.1:',self._localDeploymentPath)
		for root, dirs, files in os.walk(self._localDeploymentPath):
		    for file in files:
		        if file.endswith(".htm"):
		             log.info('level 6:',os.path.join(root, file))		

    def generateURLfromdf(self):
	try:
        	#log.info('tools:        ', self.build_cfg.tools().artifact_deployer())
	        #log.info('df path: ',os.path.join(self.build_cfg.gen_dir(),'export','export.df'))
       		#log.info('df path2: ',os.path.join(self.build_cfg.gen_dir(),'..','export','export.df'))
	        art_deployer_tool = self.build_cfg.tools().artifact_deployer()
        	art_df_path = os.path.join(self.build_cfg.gen_dir(),'..','export','export.df')
		full_cmd = [art_deployer_tool,"showpackage","-p",art_df_path]
		p = subprocess.Popen(full_cmd, stdout=subprocess.PIPE)
		result = p.communicate()[0]

		try:
		    lines = result.split('\n')
		except AttributeError:
		    lines = result
		for line in lines:
        		line = line.strip()
		        values = line.split(' ')
        	        valueUsed = values[1].replace("\'","")
        		if line.startswith('group '):
				artifact_groupId = valueUsed
				artifact_groupId_forUrl = artifact_groupId.replace(".","/")
		        elif line.startswith('artifact '):
				artifact_artifactId = valueUsed
		        elif '-ota.htm' in line:
				otaFileName = valueUsed

	        artifactFolderPath = self.create_artifactREdirectFolderStructure_fordf(artifact_groupId, artifact_artifactId)
	
		#log.info("EXPORT_REPO:",self.build_cfg.export_repo())
		#log.info("verrssonss: ",self.build_cfg._version)
	
        	keyURLAutomatic = self.build_cfg.export_repo()+artifact_groupId_forUrl+"/"+artifact_artifactId+"/"+self.build_cfg.base_version()+"/"+otaFileName
		#log.info('automatic: ',keyURLAutomatic)
        	htmlurl = HTML_TEMPLATE.replace("$LOCATION",keyURLAutomatic)
	        artifactFileFullName = keyURLAutomatic.rpartition('/')[2]
        	artifactName = self.getRedirectHtmlFilename(artifactFileFullName, artifact_artifactId)
	        #log.info(artifactFileFullName)
        	#log.info(artifactName)
	        self.createHTMLFileforArtifacts(artifactName, artifactFolderPath, htmlurl)
	except Exception:
		pass

    def after_EXPORT(self, build_cfg):
	log.info('expo repo: ', self.build_cfg.export_repo())
	if 'releases' in self.build_cfg.export_repo() or 'milestones' in self.build_cfg.export_repo():
	#if self.build_cfg.export_repo().find('releases') or self.build_cfg.export_repo().find('milestones'):
	#if self.build_cfg.is_release() is None:
		art_df_path = os.path.join(self.build_cfg.gen_dir(),'..','export','export.df')
                if os.path.exists(art_df_path):
                        self.generateURLfromdf()
	else:
		log.info('Snapshot repo!')

    def create_artifactREdirectFolderStructure_fordf(self, artifact_groupId, artifact_artifactId):
        if os.path.exists(self.build_cfg.gen_dir()):
                artifact_dir = r"artifactsRedirect/artifacts/tmpOta"
		otatxt = r"artifactsRedirect/artifacts/tmpOta/TemporaryOTA_READme.txt"
		otatxtFile = os.path.join(self.build_cfg.gen_dir(), otatxt)
                artifactFolder = os.path.join(self.build_cfg.gen_dir(), artifact_dir, artifact_groupId, artifact_artifactId)
                if not os.path.exists(artifactFolder):
                        os.makedirs(artifactFolder)
			#creating .txt for temporary OTA file
	                text_file = open(otatxtFile, "w")
        	        text_file.write("WARNING- This is a temporary OTA file which is being created by forming the nexus link to your specified version of artifact. Use only if you are unable to see the deployed OTA.")
                	text_file.close()
                return artifactFolder	
