import os
import inst
import xml.etree.ElementTree as ET
from os.path import join, isfile
from string import Template

import log
import config
from ExternalTools import OS_Utils
from xmake_exceptions import XmakeException

class MtaTool:
    def __init__(self, build_plugin, toolid, version, options):
        self.build_plugin=build_plugin     

        self._toolid=toolid
        self._version=version
        self._options=options

        self._user_home_dir = join(self.build_plugin.build_cfg.temp_dir(), 'user.home')
        self.build_plugin.java_exec_env.env['HOME'] = self._user_home_dir

class GruntTool(MtaTool):
    def __init__(self, build_plugin, toolid, version, options):
        MtaTool.__init__(self, build_plugin, toolid, version, options)

        cwd=os.getcwd()
        try:
            os.chdir( self.build_plugin.build_cfg.component_dir())
            rc=self.build_plugin.java_exec_env.log_execute(["npm"+("" if OS_Utils.is_UNIX() else ".cmd"),"install","--global","grunt-cli"])
            if rc > 0:
                raise XmakeException('mta returned %s' % str(rc))
        finally:
            os.chdir(cwd)
                
class NodeTool(MtaTool):
    def __init__(self, build_plugin, toolid, version, options):
        MtaTool.__init__(self, build_plugin, toolid, version, options)

        self._nodehome = self.build_plugin.build_cfg.tools()[self._toolid][self._version]
        self._npm_prefix_dir = join(self.build_plugin.build_cfg.temp_dir(), '.npm-global')
        self._node_rel_path = 'bin'
        self._npm_rel_path = 'lib'        
        
        dirs = os.listdir(self._nodehome)
        if len(dirs) != 1:
            raise XmakeException('ERR: invalid nodejs distribution %s' % str(self._nodehome))
        self._nodehome = join(self._nodehome, dirs[0])
        log.info('found node: ' + self._nodehome)

        self._path = os.path.realpath(os.path.join(self._nodehome, self._node_rel_path))+os.pathsep+os.path.realpath(os.path.join(self._nodehome, self._npm_rel_path))
        self._node_executable = os.path.realpath(self._node_cmd())
        self._npmrc_file = os.path.join(self._user_home_dir, '.npmrc')
        # self._npmcmd = [self._node_executable, '-i', os.path.realpath(self._npm_script()), '--userconfig', self._npmrc_file]

        self.module_dir = join(self.build_plugin.build_cfg.gen_dir(), 'module')
        self.shrinkwrap = join(self.build_plugin.build_cfg.temp_dir(), 'npm-shrinkwrap.json')
        # self.build_plugin.build_cfg.add_metadata_file(self.shrinkwrap)
        self._node_setup_env()
        self.prepare_npmrc()
        
    def _node_setup_env(self):
        
        env = self.build_plugin.java_exec_env.env
        prop = 'PATH'
        if prop not in env:
            prop = 'path'

        p=self._path+os.pathsep+self._npm_prefix_dir+os.pathsep+os.path.join(self._npm_prefix_dir, 'bin')

        env[prop] = p+(os.pathsep+env[prop] if prop in env else "")
        log.info('adding '+p+' to '+prop)
        env['XMAKE_IMPORT_DIR'] = self.build_plugin.build_cfg.import_dir()
        log.info('adding '+self._npm_prefix_dir+' to NPM_CONFIG_PREFIX')
        env['NPM_CONFIG_PREFIX'] = self._npm_prefix_dir
        log.info('forcing '+self._npmrc_file+' as .npmrc file to be consumed')
        env['npm_config_userconfig'] = self._npmrc_file

        def add_tool(n, d):
            prop = self._node_tool_property(n)
            log.info('  adding env property '+prop)
            env[prop] = d
        self.build_plugin._handle_configured_tools(add_tool)
                
    def _node_tool_property(self, key):
        return 'TOOL_' + key + '_DIR'
    
    def _node_cmd(self, nodehome=None):
        if nodehome is None:
            nodehome = self._nodehome
        return os.path.join(nodehome, self._node_rel_path, self.build_plugin.build_cfg.tools().executable('node', 'exe'))

    def prepare_npmrc(self):
        log.info('write .npmrc settings in ' + self._npmrc_file)
        with open(self._npmrc_file, 'w') as f:
            if self.build_plugin.build_cfg.import_repos(config.NPMREPO) and len(self.build_plugin.build_cfg.import_repos(config.NPMREPO)): 
                log.info('\tregistry will be ' + self.build_plugin.build_cfg.import_repos(config.NPMREPO)[0])
                f.write('registry='+self.build_plugin.build_cfg.import_repos(config.NPMREPO)[0]+'\n')
            f.write('prefix='+self._npm_prefix_dir+'\n')
            
class MavenTool(MtaTool):
    def __init__(self, build_plugin, toolid, version, options):
        MtaTool.__init__(self, build_plugin, toolid, version, options)
        '''
            Setup all the attributes of the class        '''
        
        self._maven_settings_noproxy = None

        for entry in self._options:
            o=entry.split('=')
            if o and len(o)==2:
                if o[0]=='noproxy': self._maven_settings_noproxy = o[1] and o[1].lower() in ('true', 'y', 'yes')
        
        self._m2_home = self.build_plugin.build_cfg.tools()[self._toolid][self._version]
        self._maven_cmd = self._find_maven_executable()
        log.info('found maven: ' + self._maven_cmd)
        self._dotm2_dir = join(self._user_home_dir, '.m2')
        self._maven_settings_xml_file = join(self._dotm2_dir, 'settings.xml')
        self._maven_jvm_options = ['-Djavax.net.ssl.trustStore='+join(inst.get_installation_dir(), 'xmake', 'template', 'maven', 'keystore'),
                                   '-Dmaven.wagon.http.ssl.insecure=true',  # Use keystore because these two VM options have no effect on maven...
                                   '-Dmaven.wagon.http.ssl.allowall=true']  # Also tried to use maven_jvm_opS but no effect as well
        self._maven_build_dependencies_file = join(self.build_plugin.build_cfg.temp_dir(), 'dependencies')
        self._maven_repository_dir = join(self.build_plugin.build_cfg.temp_dir(), 'repository')
        self._setup_settings_xml()
        self.build_plugin.java_exec_env.env['VERSION'] = self.build_plugin.build_cfg.base_version()
        self.build_plugin.java_exec_env.env['REPOSITORY'] = self._maven_repository_dir
        self.build_plugin.java_exec_env.env['MAVEN_OPTS'] = (self.build_plugin.java_exec_env.env['MAVEN_OPTS']+' ' if 'MAVEN_OPTS' in self.build_plugin.java_exec_env.env else '')+'-Duser.home='+self._user_home_dir+' -Dmaven.repo.local='+self._maven_repository_dir

        if self._m2_home:
            self.build_plugin.java_exec_env.env['M2_HOME'] = self._m2_home

            m2_bin = os.path.join(self._m2_home, 'bin')
            path = self.build_plugin.java_exec_env.env['PATH']
            if path is None:
                self.build_plugin.java_exec_env.env['PATH'] = m2_bin
            elif path.find(m2_bin) < 0:
                self.build_plugin.java_exec_env.env['PATH'] = os.pathsep.join([m2_bin, path])
    
    def _find_maven_executable(self):
        '''
            Find the mvn command path according to the operating system
        '''

        if OS_Utils.is_UNIX():
            path = join(self._m2_home, 'bin', 'mvn')
        else:
            path = join(self._m2_home, 'bin', 'mvn.cmd')
            if not os.path.isfile(path):
                path = join(self._m2_home, 'bin', 'mvn.bat')
        return path

    def _setup_settings_xml(self):
        '''
            Build a custom settings.xml file from a template located in [install_dir]/xmake/template/maven/settings.xml
            Mainly two fields are customized:
             - localRepository
             - mirrors: adding <mirror> one per import repository
            This new file is saved into [component_dir]/gen/tmp/settings.xml
        '''

        # Add xml namespaces
        ET.register_namespace('', 'http://maven.apache.org/SETTINGS/1.0.0')
        ET.register_namespace('xsi', 'http://www.w3.org/2001/XMLSchema-instance')
        ET.register_namespace('xsi:schemaLocation', 'http://maven.apache.org/SETTINGS/1.0.0 http://maven.apache.org/xsd/settings-1.0.0.xsd')

        # Parse template/settings.xml
        templateSettingsXmlFile = join(os.path.dirname(os.path.realpath(__file__)), 'mtatemplate', 'settings.xml')
        xmlSettingsContent = ''
        with open(templateSettingsXmlFile, 'r') as f:
            xmlSettingsContent = f.read()

        xmlSettingsContent = Template(xmlSettingsContent).substitute(
            proxyactivated='false' if self._maven_settings_noproxy else 'true', 
            mavensettingsxml=self._maven_settings_xml_file)

        tree = ET.fromstring(xmlSettingsContent)
        if tree is None:
            raise XmakeException('cannot generate specific settings.xml for maven')

        # Search fileds to update
        namespace = '{http://maven.apache.org/SETTINGS/1.0.0}'
        localRepository = tree.find('./{}localRepository'.format(namespace))
        mirrorsUrl = tree.find('./{0}mirrors'.format(namespace))
        sonarproperties = tree.find('./{0}profiles/{0}profile[{0}id="sonar"]/{0}properties'.format(namespace))
        sonarjdbcurl = sonarproperties.find('{0}sonar.jdbc.url'.format(namespace))
        sonarjdbcdriver = sonarproperties.find('{0}sonar.jdbc.driver'.format(namespace))
        sonarjdbcusername = sonarproperties.find('{0}sonar.jdbc.username'.format(namespace))
        sonarjdbcpassword = sonarproperties.find('{0}sonar.jdbc.password'.format(namespace))
        sonarhosturl = sonarproperties.find('{0}sonar.host.url'.format(namespace))
        repos = tree.find('./{0}profiles/{0}profile[{0}id="customized.repo"]/{0}repositories'.format(namespace))
        pluginrepositoryListUrl = tree.find('./{0}profiles/{0}profile[{0}id="customized.repo"]/{0}pluginRepositories'.format(namespace))

        if localRepository is None and mirrorsUrl is None:
            raise XmakeException('cannot generate specific settings.xml for maven')

        # Add specific fields
        localRepository.text = self._maven_repository_dir

        if self.build_plugin.build_cfg.is_release() is None:
            i = 1
            for repo in self.build_plugin.build_cfg.import_repos():
                pluginrepository = ET.SubElement(pluginrepositoryListUrl, 'pluginRepository')
                ET.SubElement(pluginrepository, 'id').text = 'repo%d' % i \
                    if i < len(self.build_plugin.build_cfg.import_repos()) else "central"
                ET.SubElement(pluginrepository, 'url').text = repo
                snapshots = ET.SubElement(pluginrepository, 'snapshots')
                ET.SubElement(snapshots, 'enabled').text = 'true'
                i += 1

        i = 1
        for import_repo in self.build_plugin.build_cfg.import_repos():
            additional_mirror = ET.SubElement(mirrorsUrl, 'mirror')
            ET.SubElement(additional_mirror, 'id').text = 'mirror%d' % i
            ET.SubElement(additional_mirror, 'url').text = import_repo
            ET.SubElement(additional_mirror, 'mirrorOf').text = 'repo%d' % i \
                if i < len(self.build_plugin.build_cfg.import_repos()) else "central"
            i += 1

        i = 1
        for repo in self.build_plugin.build_cfg.import_repos():
            additional_repo = ET.SubElement(repos, 'repository')
            ET.SubElement(additional_repo, 'id').text = 'repo%d' % i \
                if i < len(self.build_plugin.build_cfg.import_repos()) else "central"
            ET.SubElement(additional_repo, 'url').text = repo
            i += 1

        # sonar properties
        jdbcurl = os.getenv('SONAR_JDBC_URL')  # jdbc:mysql://ldisonarci.wdf.sap.corp:3306/sonar?useUnicode=true&characterEncoding=utf8
        jdbcdriver = os.getenv('SONAR_JDBC_DRIVER')  # com.mysql.jdbc.Driver
        jdbcusername = os.getenv('SONAR_JDBC_USERNAME')  # sonar
        jdbcpassword = os.getenv('SONAR_JDBC_PASSWORD')  # sonar
        hosturl = os.getenv('SONAR_HOST_URL')  # http://ldisonarci.wdf.sap.corp:8080/sonar

        logWarnings = []

        # Check server utl is set
        if jdbcurl is None:
            logWarnings.append('jdbc url is not set for sonar. Please set env SONAR_JDBC_URL')
        if jdbcdriver is None:
            logWarnings.append('jdbc driver is not set for sonar. Please set env SONAR_JDBC_DRIVER')
        if jdbcusername is None:
            logWarnings.append('jdbc username is not set for sonar. Please set env SONAR_JDBC_USERNAME')
        if jdbcpassword is None:
            logWarnings.append('jdbc password is not set for sona. Please set env SONAR_JDBC_PASSWORD')
        if hosturl is None:
            logWarnings.append('sonar host url is not set. Please set env SONAR_HOST_URL')

        if len(logWarnings) > 0:
            for logWarning in logWarnings:
                log.warning(logWarning, log.INFRA)
        else:
            sonarjdbcurl.text = jdbcurl
            sonarjdbcdriver.text = jdbcdriver
            sonarjdbcusername.text = jdbcusername
            sonarjdbcpassword.text = jdbcpassword
            sonarhosturl.text = hosturl

        # Write settings.xml in component/tmp directory
        log.info('write maven settings in ' + self._maven_settings_xml_file)
        if not os.path.isdir(self._dotm2_dir):
            os.makedirs(self._dotm2_dir)
        with open(self._maven_settings_xml_file, 'w') as f:
            f.write(ET.tostring(tree))
    
