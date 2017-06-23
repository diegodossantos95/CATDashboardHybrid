## build scripts must define a class 'build'

##build script to build cordova/kapsel build
## comment added for mobile secure demo
import stat
import os
import shutil
import zipfile
from shutil import copytree, ignore_patterns
import log
import fileinput
import sys
import xml.dom.minidom as minidom
import subprocess
import webbrowser
import urllib
import re
from spi import BuildPlugin
from xmake_exceptions import XmakeException
from buildplugin import default_variant_coords


BUILD_LOCATION = {
        'android': {
            'release-unsign': 'platforms/android/build/outputs/apk/android-release-unsigned.apk',
            'release-unalign': 'platforms/android/build/outputs/apk/%s-release-unalign.apk',
            'release-sign': 'platforms/android/build/outputs/apk/%s-release-sign.apk',
            'release-ota-htm': 'platforms/android/build/outputs/apk/%s-release-ota.htm',
            'release-otaref-htm': 'platforms/android/abuild/outputs/apk/%s-android-release-otaref.htm',
            'release-crosswalkarmv7':'platforms/android/build/outputs/apk/android-armv7-release-unsigned.apk',
            'release-crosswalkx86': 'platforms/android/build/outputs/apk/android-x86-release-unsigned.apk'
        },
        'ios': {
            'release-unsign': 'platforms/ios/build/device/%s.app',
            'release-unalign': 'platforms/ios/build/device/%s.app',
            'release-sign': 'platforms/ios/build/device/%s.ipa',
            'release-ota-htm': 'platforms/ios/build/device/%s-release-ota.htm',
            'release-otaref-htm': 'platforms/ios/build/device/%s-ios-release-otaref.htm'
        }
}

class build(BuildPlugin):
  def __init__(self, build_cfg):
    BuildPlugin.__init__(self,build_cfg)
    self._build_type='online'
    self._android_version='24.3.3'
    self._gradle_version='2.2.1'
    self._nodejs_version='0.10.36-SNAPSHOT'
    self._plugman_version='0.23.3'
    self._cordova_version='5.1.1'
    self._android_buildtools_version='22.0.1'
    os.environ['HTTP_PROXY']=''
    os.environ['HTTPS_PROXY']=''
    os.environ['http_proxy']=''
    os.environ['https_proxy']=''
    os.environ['ftp_proxy']=''
    os.environ['FTP_PROXY']=''
    os.environ['all_proxy']=''
    self._use_sap_kapsel_inappbrowser=False
    self._crosswalk_enabled=False
    self._crosswalk_plugin='cordova-plugin-crosswalk-webview'
    self._crosswalk_plugin_version='1.2.0'
    self._internal_registryvalue= 'registry="http://nexus.wdf.sap.corp:8081/nexus/content/repositories/build.milestones.npm/"'
    
    


  def required_tool_versions(self):
        if self.build_cfg.runtime() == "linuxx86_64":
            return {"NODEJS":self._nodejs_version,'GRADLE':self._gradle_version,"ADT":self._android_version,"ANDROID_BUILD_TOOLS":self._android_buildtools_version}
        else:
            return {"NODEJS":self._nodejs_version}

  def run(self):
    log.info( 'Building Cordova Application...' )               #this is where the custom build commands go
    os.system('unset FTP_PROXY')
    os.system('unset HTTP_PROXY')
    os.system('unset HTTPS_PROXY')
    os.system('unset ftp_proxy')
    os.system('unset http_prxoy')
    os.system('unset https_proxy')
    os.system('unset all_proxy')
    os.system('set | grep proxy')
    self.get_cordova_groupid() 
    print self.build_cfg.variant_coords()
    platform=self.build_cfg.variant_coords()["platform"]
    if platform == 'crosswalk' :
        self._crosswalk_enabled=True
    	platform = "android" 
    gen_src_dir = os.path.join(self.build_cfg.gen_dir(),"src")
    #os.makedirs(gen_src_dir)
    kapsel_plugin_dir = os.path.join(self.build_cfg.gen_dir(),"kapsel","plugins")

    self._init_cordova_project()
    '''We need to replace all subprocess call with log.execute '''
    subprocess.call(['cordova', '-v'])
    log.info('Read Cordova Config.xml and determine app name from the confix xml file:', self._get_config_xml())
    
    #
    #Add Platform
    #
    appname = self.get_cordova_appname()
    if platform == 'ios' :
        self.unlock_ios_keychain()
    
    log.info('Adding platform in Cordova: ', platform )
    os.chdir(gen_src_dir)
    if self.add_cordova_platform_online(platform):
        log.info('Success adding platform in Cordova: ', platform )
    else :
        log.error('Error in adding platform in Cordova: ', platform )
        raise XmakeException('Unable to add Cordova platform. Aborting build')
        
    self.cordova_plugin_install(kapsel_plugin_dir)
	
    
    if platform == 'android' :
    
    	gen_tools_dir = os.path.join(self._own_dir(),"tools")
    	buildgradlefile = os.path.join(gen_tools_dir,'cordova_lib','lib','npm_cache','cordova-android','4.0.2','package')
    	plugingradlefile = os.path.join(buildgradlefile,'bin','templates','cordova','lib','plugin-build.gradle')
    	buildgradlefile1 = os.path.join(buildgradlefile,'bin','templates','project','build.gradle')
    	buildgradlefile2 = os.path.join(buildgradlefile,'framework','build.gradle')
    	buildgradlefile3 = os.path.join(buildgradlefile,'test','build.gradle')
    	buildgradlefile4 = os.path.join(gen_src_dir,'platforms','android','build.gradle')
    	buildgradlefile5 = os.path.join(gen_src_dir,'platforms','android','CordovaLib','build.gradle')
    	log.info('plugingradlefile:',plugingradlefile)
    	for i, line in enumerate(fileinput.input(plugingradlefile, inplace=1)):
                        sys.stdout.write(line.replace('mavenCentral()', 'maven { url "http://nexus.wdf.sap.corp:8081/nexus/content/repositories/3rd-party.releases.maven-central.proxy/" }'))

    	for i, line in enumerate(fileinput.input(buildgradlefile1, inplace=1)):
                        sys.stdout.write(line.replace('mavenCentral()', 'maven { url "http://nexus.wdf.sap.corp:8081/nexus/content/repositories/3rd-party.releases.maven-central.proxy/" }'))
   
    	for i, line in enumerate(fileinput.input(buildgradlefile2, inplace=1)):
                        sys.stdout.write(line.replace('mavenCentral()', 'maven { url "http://nexus.wdf.sap.corp:8081/nexus/content/repositories/3rd-party.releases.maven-central.proxy/" }'))

    	for i, line in enumerate(fileinput.input(buildgradlefile3, inplace=1)):
                        sys.stdout.write(line.replace('mavenCentral()', 'maven { url "http://nexus.wdf.sap.corp:8081/nexus/content/repositories/3rd-party.releases.maven-central.proxy/" }'))

    	for i, line in enumerate(fileinput.input(buildgradlefile4, inplace=1)):
                        sys.stdout.write(line.replace('mavenCentral()', 'maven { url "http://nexus.wdf.sap.corp:8081/nexus/content/repositories/3rd-party.releases.maven-central.proxy/" }'))
   
    	for i, line in enumerate(fileinput.input(buildgradlefile5, inplace=1)):
                        sys.stdout.write(line.replace('mavenCentral()', 'maven { url "http://nexus.wdf.sap.corp:8081/nexus/content/repositories/3rd-party.releases.maven-central.proxy/" }'))
    	if self._crosswalk_enabled:
			s= self.get_cordova_groupid()
			r = re.split(r'[.]', s)
			xwalkfilename = r[-1] + "-xwalk.gradle"
	
			crosswalkpath = os.path.join(self.build_cfg.gen_dir(),"src","platforms","android","cordova-plugin-crosswalk-webview",xwalkfilename)
	
			replacestring = "http://nexus.wdf.sap.corp:8081/nexus/content/groups/build.releases"
                        orginalstring = "https://download.01.org/crosswalk/releases/crosswalk/android/maven2"
			for i, line in enumerate(fileinput.input(crosswalkpath, inplace=1)):
                            sys.stdout.write(line.replace(orginalstring, replacestring))
    if platform == 'ios':
		
	xcconfig_local_filename = os.path.join(gen_src_dir,'platforms','ios','cordova','build.xcconfig')
        with open(xcconfig_local_filename, "a") as f:
                        f.write("\nARCHS=armv7 arm64")

        for i, line in enumerate(fileinput.input(xcconfig_local_filename, inplace=1)):
                        sys.stdout.write(line.replace('Developer', 'Distribution'))  # replace 'Developer' and write

        xcconfig_release_filename = os.path.join(gen_src_dir,'platforms','ios','cordova','build-release.xcconfig')
        with open(xcconfig_release_filename, "a") as f:
                        f.write("\nARCHS=armv7 arm64")
    if self.build_cordova_project_online(platform):
        
	log.info('Success building this Cordova Project')
    else :
        log.error('Error in building this Cordova Project')
        raise XmakeException('Unable to building this Cordova Project')

    self.sign_artifact(platform)
    return 0

  def sign_artifact(self, platform):
    if platform == 'android' :
        if self._crosswalk_enabled:
            android_release_unsign_file = os.path.abspath(os.path.join(self._own_cordova_src_dir(),BUILD_LOCATION[platform]['release-crosswalkarmv7']))
            
        else:
            android_release_unsign_file = os.path.abspath(os.path.join(self._own_cordova_src_dir(),BUILD_LOCATION[platform]['release-unsign']))
            
        android_release_unalign_file = os.path.abspath(os.path.join(self._own_cordova_src_dir(),BUILD_LOCATION[platform]['release-unalign']%(self.get_cordova_appname())))
        android_release_sign_file = os.path.abspath(os.path.join(self._own_cordova_src_dir(),BUILD_LOCATION[platform]['release-sign']%(self.get_cordova_appname())))
        log.info('Signing Android apk file...')
        jarsign_return_code = subprocess.call([
            'jarsigner', '-verbose', '-sigalg', 'SHA1withRSA','-digestalg','SHA1', '-keystore',self._get_android_local_keystore(),android_release_unsign_file,'testkapsel','-signedjar', android_release_unalign_file,'-storepass', 'kapsel'
        ])

        if jarsign_return_code == 0:
            log.info('SUCCESS - Android Jar signing successfully done')
        else:
            log.warning('FAILURE - Android Jar signing Unsuccessfully')
        zipalign_return_code = subprocess.call([
            'zipalign', '-v', '4', android_release_unalign_file, android_release_sign_file
            ])
        
        log.info('Aliging Android apk file...')
        if zipalign_return_code == 0:
            log.info('SUCCESS - Android application align successfully done')
        else:
            log.warning('FAILURE - Android application align Unsuccessfully')
        
    if platform == 'ios' :
        ios_release_unsign_file = os.path.abspath(os.path.join(self._own_cordova_src_dir(),BUILD_LOCATION[platform]['release-unsign']%(self.get_cordova_appname())))
        ios_release_sign_file = os.path.abspath(os.path.join(self._own_cordova_src_dir(),BUILD_LOCATION[platform]['release-sign']%(self.get_cordova_appname())))
        log.info('Signing iOS app file...')
        ios_codesign= '"iPhone Distribution: SAP AG"'
        ios_provision_profile_dir = '/Users/' + os.environ['USER'] + '/Library/MobileDevice/Provisioning Profiles/' 
	for file in os.listdir(ios_provision_profile_dir):
	    if file.startswith("SAP_AG_Generic_Distribution_Profile"):
		ios_provision_profile_file= ios_provision_profile_dir.replace("Provisioning Profiles","Provisioning\ Profiles") + file      
                log.info('Using provisioning profile:',ios_provision_profile_file)
        cordovaiospackcmd = '/usr/bin/xcrun -sdk iphoneos PackageApplication -v ' + ios_release_unsign_file + ' -o ' + ios_release_sign_file + ' --embed ' + ios_provision_profile_file + ' --sign ' + ios_codesign
        log.info(cordovaiospackcmd)
        
        os.system(cordovaiospackcmd)
        self.create_ios_otahtml()
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
  
  def cordova_plugin_install(self, plug_dir):
    log.info('Install Cordova and/or Kapsel Plugins...')
    log.info('Determine plugin to install from:', self._get_config_xml())
    if self._crosswalk_enabled:
        if self.add_cordova_plugin_online(self._crosswalk_plugin, self._crosswalk_plugin_version):
            log.info('Success adding plugin in Cordova: ', self._crosswalk_plugin )
        else:
            log.error('Error in adding crosswalk plugins in Cordova. Please check build log for more details ' )
            raise XmakeException('Unable to add Crosswalk plugins. Aborting build')
    if not self._use_sap_kapsel_inappbrowser:
        inappbrowser_plugin_xml=os.path.join(self.build_cfg.gen_dir(),"kapsel","plugins","inappbrowser","plugin.xml")
        inappbrowser_plugin_xml_old = inappbrowser_plugin_xml + ".old"
        os.rename(inappbrowser_plugin_xml,inappbrowser_plugin_xml_old)
    else:
        inappbrowser_plugin_src_folder=os.path.join(self.build_cfg.gen_dir(),"kapsel","plugins","inappbrowser")
        inappbrowser_plugin_dest_folder=os.path.join(self._own_cordova_src_dir(),"plugins","org.apache.cordova.inappbrowser")
        shutil.copytree(inappbrowser_plugin_src_folder, inappbrowser_plugin_dest_folder, symlinks=False, ignore=None)
    xmldoc = minidom.parse(self._get_config_xml())
    #kapsel_plugin_list = xmldoc.getElementsByTagName('feature')
    kapsel_plugin_list = xmldoc.getElementsByTagName('plugin')
    if kapsel_plugin_list:
        plugin_install_flag = 1
        for kapsel_plugin in kapsel_plugin_list :
            #plugin = kapsel_plugin.getElementsByTagName('param')[0].getAttribute('value')
            plugin = kapsel_plugin.getAttribute('name')
            plugin_version = kapsel_plugin.getAttribute('spec')
            plug_version= re.findall('[0-9]+\.[0-9]+\.[0-9]+',plugin_version, re.M|re.I)[0]
            log.info('Installing plugin:', plugin,plug_version)
            if self.add_cordova_plugin_online(plugin, plug_version):
                plugin_install_flag &= 1
                log.info('Success adding plugin in Cordova: ', plugin )
            else :
                plugin_install_flag &= 0
                log.warning('Couldnt add plugin in Cordova: ', plugin )
        if plugin_install_flag:
            log.info('All Plugins Successfully added')
        else:
            log.error('Error in adding plugins in Cordova. Please check build log for more details ' )
            raise XmakeException('Unable to add Cordova plugins. Aborting build')
    else:
        log.warning('No Plugin information is available in src/config.xml. Please run command \'cordova --experimental save plugins\' in you machine and checkin the new config.xml file')

  def after_IMPORT(self, build_cfg):
    self._clean_home()
    
    plugman_parent_dir = os.path.join(os.environ['HOME'],".npm")
    plugman_dir = os.path.join(os.environ['HOME'],".npm")
    if not os.path.exists(plugman_parent_dir):
        os.makedirs(plugman_parent_dir)
	
    kapsel_plugin_zip = os.path.join(self.build_cfg.import_dir(),"smp-plugins-dist-3.13.0-sap-13.zip")
    kapsel_plugin_dir = os.path.join(self.build_cfg.gen_dir(),"kapsel")
    if not os.path.exists(kapsel_plugin_dir):
        os.makedirs(kapsel_plugin_dir)
    with zipfile.ZipFile(kapsel_plugin_zip, "r") as z:
        z.extractall(kapsel_plugin_dir)
        os.chmod(kapsel_plugin_dir,0755)        
            
    if self.build_cfg.runtime() == "linuxx86_64":
        self._adttools=os.path.join( self.build_cfg.tools()['ADT'][self._android_version], "adt","sdk", "tools" )
	self._adttoolshome=os.path.join( self.build_cfg.tools()['ADT'][self._android_version], "adt","sdk" )

	#self._adttools=os.path.join( os.environ["HOME"], "andriod","adt", "sdk","tools" )
        log.info( self._adttools )
	os.environ["ANDROID_HOME"]=self._adttoolshome
        self._adt_platformtools=os.path.join( self.build_cfg.tools()['ADT'][self._android_version], "adt","sdk", "platform-tools" )
        log.info( self._adt_platformtools)
        self._adt_buildtools_parent=os.path.join( self.build_cfg.tools()['ADT'][self._android_version], "adt","sdk", "build-tools")
        self._adt_buildtools=os.path.join( self.build_cfg.tools()['ADT'][self._android_version], "adt","sdk", "build-tools", "22.0.1" )
        log.info( self._adt_buildtools )
        self._gradlebin=os.path.join( self.build_cfg.tools()['GRADLE'][self._gradle_version],"gradle-2.2.1", "bin" )
        log.info( self._gradlebin )
        self._nodejsbin=os.path.join( self.build_cfg.tools()["NODEJS"][self._nodejs_version],"bin")
        log.info( self._nodejsbin )
        self._adt_build_tool=os.path.join( self.build_cfg.tools()["ANDROID_BUILD_TOOLS"][self._android_buildtools_version],"android-5.1")
        log.info( self._adt_build_tool )
        os.environ['GRADLE_USER_HOME']=self.build_cfg.tools()['GRADLE'][self._gradle_version]
        log.info("gradle user home path ", os.environ['GRADLE_USER_HOME'])
	self._android_build_dest=os.path.join(self._adt_buildtools_parent, self._android_buildtools_version)
        if not os.path.exists(self._android_build_dest):
            shutil.copytree(self._adt_build_tool, self._android_build_dest, symlinks=False, ignore=None)
            chmod_cmd ='chmod -R 0755 ' + self._android_build_dest
            os.system(chmod_cmd)
        os.environ["PATH"] += os.pathsep + self._gradlebin + os.pathsep + self._nodejsbin + os.pathsep + self._adttools + os.pathsep + self._adt_platformtools + os.pathsep + self._adt_buildtools + os.pathsep + self._adt_build_tool
    else:
        self._nodejsbin=os.path.join( self.build_cfg.tools()["NODEJS"][self._nodejs_version],"bin" )
        log.info( self._nodejsbin )
        os.environ["PATH"] += os.pathsep + self._nodejsbin

    #self._cordovaexe=os.path.join( self.build_cfg.tools()["CORDOVA"][self._cordova_version],"cordova", "bin", "cordova" )
    #self._cordova_path=os.path.join( self.build_cfg.tools()["CORDOVA"][self._cordova_version],"cordova", "bin")
    #log.info( self._cordovaexe )
    #self._plugman_path=os.path.join( self.build_cfg.tools()["PLUGMAN"][self._plugman_version],"plugman","main.js")
    #log.info( self._plugman_path )
    
    #TODO: os.environ["PATH"] = self._cordova_path + os.pathsep + os.environ["PATH"]
    #self._cordovaplugins=self.build_cfg.tools()["CORDOVA_PLUGINS"][self._cordova_version]
    #log.info( self._cordovaplugins )
    
    #self._cordovatemplate=os.path.join( self.build_cfg.tools()["CORDOVA_TEMPLATES"][self._cordova_version],"lib","npm_cache")
    #log.info( self._cordovatemplate )
    
    #if not os.path.exists(os.path.join(self._nodejsbin, "cordova")): 
    #    os.symlink(self._cordovaexe, os.path.join(self._nodejsbin, "cordova"))
    #if not os.path.exists(os.path.join(self._nodejsbin, "plugman")): 
    #    os.symlink(self._plugman_path, os.path.join(self._nodejsbin, "plugman"))
    #
    #if not os.path.exists(plugman_dir): 
    #    os.symlink(self._cordovaplugins, plugman_dir)
    #    subprocess.call(['chmod', '-R', '755', self._cordovaplugins])
    #if not os.path.exists(cordova_template_dir): 
    #    os.symlink(self._cordovatemplate, cordova_template_dir)
    #    subprocess.call(['chmod', '-R', '755', self._cordovatemplate])
    print os.environ['PATH']
	
  def set_npm_registry(self):
    log.info("setting the npm registry")
    os.chdir(self._nodejsbin)
    log.info("environment path : ",os.environ["PATH"])
    npmregistry_return_code = subprocess.call(['./npm', 'set', self._internal_registryvalue])
    if npmregistry_return_code == 0:
        log.info("Success: npm registry set")
    else:
        log.error("FAILURE: Failed to set npm registry") 
  def _init_cordova_project(self):
    log.info('Preparing the Cordova project')
    gen_src_dir = os.path.join(self._own_dir(),"src")
    if not os.path.exists(gen_src_dir):
        os.makedirs(gen_src_dir)
    gen_tools_dir = os.path.join(self._own_dir(),"tools")
    if not os.path.exists(gen_tools_dir):
        os.makedirs(gen_tools_dir)
		
    self.set_npm_registry()

    #We are merging the content of sh file to build.py
    #Install cordova and plugman
    log.info("INFO:Started merging the logic of shell script into py")   
    log.info("INFOG1:",gen_tools_dir)	
#    os.chdir(gen_tools_dir)    
	#setup the proxy required
#    log.info("INFOG2:"+os.environ["PATH"])		
#    https_proxy_set_return_code = subprocess.call(['npm','config','set','https-proxy','http://proxy.wdf.sap.corp:8080'])
#    log.info("INFOG3:",https_proxy_set_return_code)		
#    http_proxy_set_return_code = subprocess.call(['npm','config','set','http-proxy','http://proxy.wdf.sap.corp:8080'])
#    log.info("INFOG4:",http_proxy_set_return_code)		
#    if https_proxy_set_return_code == 0 and http_proxy_set_return_code == 0:
#        log.info("Success:NPM_Proxy: set")
#    else:
#        log.error("FAILURE:NPM_Proxy: Failed to set the npm proxy")   
    
    #Installing cordova, we are installing it in gen_src_dir
    os.chdir(self._nodejsbin)
    os.system('pwd')
    log.info("environment path : ",os.environ["PATH"])
    try :
          os.remove(os.path.join(self._nodejsbin, "cordova"))
    except OSError, e :
          log.info(e.errno)
          pass
		
    try :
          os.remove(os.path.join(self._nodejsbin, "plugman"))
    except OSError, e :
          log.info(e.errno)
          pass
    install_cordova_return_code = subprocess.call(['./npm','install','-g','cordova@5.1.1','--verbose'])
    if install_cordova_return_code == 0:
        log.info("Success:InstallCordova: Cordova is installed")
        os.environ["CORDOVA_HOME"]=os.path.join(gen_tools_dir,"cordova_lib")
    else:
        log.error("FAILURE:InstallCordova: Failed to set install cordova")
    #Installing plugman, we are installing it in gen_src_dir
    
    install_plugman_return_code = subprocess.call(['./npm','install','plugman@0.23.3','--verbose'])
    if install_plugman_return_code == 0:
        log.info("Success:InstallPlugman: Plugman is installed")
        os.environ["PLUGMAN_HOME"]=os.path.join(gen_tools_dir,"plugman_lib")
    else:
        log.error("FAILURE:InstallPlugman: Failed to set install plugman")     
	log.info("INFO:End of merging the logic of shell script into py")
    #End of sh file content merging 
    #Adding cordova and plugman into PATH as this was not working in iOS, but it was working without these in Andriod and crosswalk, we can try if it works with these in andriod otherwsie we have to do these based on if for ios
    self._cordova_path=os.path.join( self.build_cfg.tools()["NODEJS"][self._nodejs_version],"bin","node_modules","cordova", "bin")
    #log.info('Adding cordova bin to PATH',self._cordova_path)
    #os.environ["PATH"] += os.pathsep + self._cordova_path
    self._plugman_path=os.path.join( self.build_cfg.tools()["NODEJS"][self._nodejs_version],"bin","node_modules","plugman","main.js")
    #if not os.path.exists(os.path.join(self._nodejsbin, "cordova")):
    #    os.symlink(self._cordova_path, os.path.join(self._nodejsbin, "cordova"))
    if not os.path.exists(os.path.join(self._nodejsbin, "plugman")):
        os.symlink(self._plugman_path, os.path.join(self._nodejsbin, "plugman"))
    log.info('Creating Cordova Project Structure in ', gen_src_dir)
    plugin_search_path = "{\"plugin_search_path\":\"" + os.path.join(self.build_cfg.gen_dir(),"kapsel","plugins") + "\"}"
    return_code = subprocess.call([
        'cordova', 'create', gen_src_dir, self.get_cordova_groupid(), self.get_cordova_appname(),'--copy-from', self._own_src_dir(), plugin_search_path,'-d'
    ])

    if return_code == 0:
        return True
    else:
        return False


  def _clean_home(self):
        log.info('purging .cordova and .plugin directory in %HOME% or %HOME%"')
        kapsel_plugin_dir = os.path.join(self.build_cfg.import_dir(),"kapsel")
        if (os.path.exists(kapsel_plugin_dir)):
            shutil.rmtree(kapsel_plugin_dir)


  def add_cordova_platform(self, platform):
    if platform =="ios":
        self._cordova_iphone_exe = os.path.join(os.environ['HOME'],".cordova","lib","npm_cache","cordova-ios","3.8.0","package","bin","create")
        self._project_iphone_folder = os.path.join(self._own_cordova_src_dir(),"platforms","ios")
        return_code = subprocess.call([
                self._cordova_iphone_exe, '--cli', self._project_iphone_folder, self.get_cordova_groupid(),self.get_cordova_appname()
        ])
    if platform =="android":
        self._cordova_android_exe = os.path.join(os.environ['HOME'],".cordova","lib","npm_cache","cordova-android","4.0.2","package","bin","create")
        self._project_android_folder = os.path.join(self._own_cordova_src_dir(),"platforms","android")
        log.info('before adding android platform',self._cordova_android_exe, self._project_android_folder)
        return_code = subprocess.call([
                self._cordova_android_exe, '--cli', self._project_android_folder, self.get_cordova_groupid(),self.get_cordova_appname()
        ])
    
    #/sapmnt/ppurple/.cordova/lib/npm_cache/cordova-android/4.0.2/package/bin/create --cli /mnt/jenkinsSlaveWorkspace/xmakeProdSlave/workspace/cdvtest/hello/platforms/android com.sap.kapsel HelloWorld
    if return_code == 0:
        return True
    else:
        return False

  def add_cordova_platform_online(self, platform):
    if platform =="ios":
        gen_src_dir = os.path.join(self.build_cfg.gen_dir(),"src")
        os.chdir(gen_src_dir)
        log.info('adding platform in gen src dir',gen_src_dir)
        return_code = subprocess.call([
                'cordova', 'platform', 'add','ios','-d'  ])
    if platform =="android":
	gen_src_dir = os.path.join(self.build_cfg.gen_dir(),"src")	
        os.chdir(gen_src_dir)
	log.info('adding platform in gen src dir',gen_src_dir)
        return_code = subprocess.call([
                'cordova', 'platform', 'add','android','-d'  ])
    if return_code == 0:
        return True
    else:
        return False

  def remove_cordova_platform(self, platform):
        return_code = subprocess.call([
                'cordova', 'platform', 'remove', platform
        ])

        if return_code == 0:
                return True
        else:
                return False
  def add_cordova_plugin_online(self, plugin, plugin_version):
    self._project_platform_folder = os.path.join(self._own_cordova_src_dir(),"platforms",self._get_platform())
    self._project_plugins_folder = os.path.join(self._own_cordova_src_dir(),"plugins")

    if 'kapsel-' in plugin:
        searchObj = re.search( r'kapsel-plugin-(.*)', plugin, re.M|re.I)
        if searchObj:
            kapsel_plugin_folder= searchObj.group(1)

        self._plugin_folder = os.path.join(self.build_cfg.gen_dir(),"kapsel","plugins",kapsel_plugin_folder)
    	return_code = subprocess.call([
        'plugman', 'install', '--platform', self._get_platform(),'--project',self._project_platform_folder,'--plugin',self._plugin_folder, "--plugins_dir",self._project_plugins_folder,'-d'
    ])
    else:
	gen_src_dir = os.path.join(self.build_cfg.gen_dir(),"src")
	os.chdir(gen_src_dir)
	plugin_with_version = plugin#+"@"+plugin_version
	#return_code = subprocess.call(['cordova', 'plugin', 'add', plugin_with_version])
	return_code = subprocess.call([
        'plugman', 'install', '--platform', self._get_platform(),'--project',self._project_platform_folder,'--plugin',plugin_with_version, "--plugins_dir",self._project_plugins_folder,'-d'
    ])

    if return_code == 0:
        return True
    else:
        return False
  def add_cordova_plugin(self, plugin, plugin_version):
    self._project_platform_folder = os.path.join(self._own_cordova_src_dir(),"platforms",self._get_platform())
    self._project_plugins_folder = os.path.join(self._own_cordova_src_dir(),"plugins")
    
    if 'kapsel-' in plugin:
        searchObj = re.search( r'kapsel-plugin-(.*)', plugin, re.M|re.I)
        if searchObj:
            kapsel_plugin_folder= searchObj.group(1)
        
        self._plugin_folder = os.path.join(self.build_cfg.gen_dir(),"kapsel","plugins",kapsel_plugin_folder)
    else:
        self._plugin_folder = os.path.join (self.build_cfg.tools()["CORDOVA_PLUGINS"][self._cordova_version],plugin,plugin_version,"package")
    
    return_code = subprocess.call([
        'plugman', 'install', '--platform', self._get_platform(),'--project',self._project_platform_folder,'--plugin',self._plugin_folder, "--plugins_dir",self._project_plugins_folder,'-d'
    ])
        #plugman  install --platform android --project /var/cordova/cdv55/hello/platforms/android/ --plugin cordova-plugin-camera --plugins_dir /var/cordova/cdv55/hello/plugins/
        
    if return_code == 0:
        return True
    else:
        return False
  def remove_cordova_plugin(self, plugin):
        return_code = subprocess.call([
                'cordova', 'plugin', 'remove', plugin
        ])

        if return_code == 0:
                return True
        else:
                return False
  def build_cordova_project_online(self, platform):
    if platform =="ios":
        return_code = subprocess.call([
            'cordova', 'build','ios','--device','--release','-d'
        ])
    if platform =="android":
        return_code = subprocess.call([
            'cordova', 'build', 'android','--device','--release','-d','--'#,'--gradleArg=--offline'
        ])
    if return_code == 0:
        return True
    else:
        return False
  def build_cordova_project(self, platform):
    if platform =="ios":
        return_code = subprocess.call([
            'cordova', 'compile', '--device', '--release','-d'
        ])
    if platform =="android":
        return_code = subprocess.call([
            'cordova', 'compile', 'android','--device', '--release','-d','--'#,'--gradleArg=--offline'
        ])
    if return_code == 0:
        return True
    else:
        return False
  def variant_cosy(self):
        #return 'kapsel:1'
        #return None
    return os.path.join(self.build_cfg.cfg_dir(), 'kapsel-1.variant-coordinate-system')

  def variant_coords(self):
        return default_variant_coords(self.build_cfg)

  

  def deploy_variables(self):
    if self._get_platform() == 'ios' :
        ipa_file_name = self.get_cordova_appname() + '.ipa'
        ota_file_name = self.get_cordova_appname() + '-release-ota.htm'
        return {'groupId': self.get_cordova_groupid(), 
            'artifactId' : self.get_cordova_appname(),
            'file' : os.path.join(self._own_dir(), 'src','platforms',self._get_platform(),'build','device',ipa_file_name),
            'otafile' : os.path.join(self._own_dir(), 'src','platforms',self._get_platform(),'build','device',ota_file_name),
            'classifierId' : 'release'}
    if self._get_platform() == 'android' :
        apk_file_name = self.get_cordova_appname() + '-release-sign.apk'
        return {'groupId': self.get_cordova_groupid(), 
            'artifactId' : self.get_cordova_appname(),
            'file' : os.path.join(self._own_dir(), 'src','platforms',self._get_platform(),'build','outputs','apk',apk_file_name),
            'classifierId' : 'release'}

  def _get_config_xml(self):
    config_xml_location = os.path.abspath(os.path.join(self.build_cfg.src_dir(),"config.xml"))
    if os.path.exists(config_xml_location):
        log.info('Cordova Config XML found at: ', config_xml_location )
        return config_xml_location
    else :
        log.error('Cordova Config XML not found in the src folder' )
        raise XmakeException('Unable to locate cordova config xml. Aborting build')
        
  def _get_android_local_keystore(self):
    keystore_location = os.path.abspath(os.path.join(self.build_cfg.cfg_dir(),"testkapsel.keystore"))
    if os.path.exists(keystore_location):
        log.info('Keystore file to sign Android apk is found at : ', keystore_location )
        return keystore_location
    else :
        log.warning('Cannot sign Android application. Keystore file to sign Android apk is not found at', keystore_location)
        
  def get_cordova_appname(self):
    config_xmldoc = minidom.parse(self._get_config_xml())
    for node in config_xmldoc.getElementsByTagName('name'):
        appname = node.childNodes[0].nodeValue
    return appname

  def get_cordova_groupid(self):
    config_xmldoc = minidom.parse(self._get_config_xml())
    groupid = config_xmldoc.firstChild.getAttribute('id')
    log.info('Groupid for app name found in config.xml is: ', groupid)
    return groupid
    
  def _get_platform(self): 
    if self.build_cfg.runtime() == "linuxx86_64":
        return "android"
    if self.build_cfg.runtime() == "darwinintel64":
        return "ios"

  def create_ios_otahtml(self):
    log.info('Creating Over the Air installer for IOS')
    gen_src_dir = os.path.join(self.build_cfg.gen_dir(),"src")
    ios_ota_path = os.path.abspath(os.path.join(gen_src_dir,"platforms","ios","build","device",self.get_cordova_appname()))
    ios_ota_file = ios_ota_path + '-release-ota.htm'
    otagroupid = self.get_cordova_groupid()
    otaappname = self.get_cordova_appname()
    otaversion = self.build_cfg.version()
    f = open(ios_ota_file,'w')
    html = """\
    <html>
            <head>
                    <title>OTA Install Page</title>
                    <meta name="scm-type" content="git">
                    <meta name="repo" content="ssh://git.wdf.sap.corp:29418/prod/iOS/main.git">
                    <meta name="branch" content="ota-service-sap-template">
                    <style>
                            .buildInfo {
                                    font-family: sans-serif;
                                    font-size: 7pt;
                                    color: grey;
                                    border-style:none;
                            }
                    </style>
            </head>
            <body>
                    <iframe id="iframe" src="https://apple-ota.wdf.sap.corp:8443/ota-service/HTML?title=@otaappname@&bundleIdentifier=@otagroupid@&bundleVersion=@otaversion@&ipaClassifier=release&otaClassifier=release-ota" width="700px" height="450px" marginheight="0" marginwidth="0" frameborder="0">
                            <b>Click below to open OTA Installer Page</b>
                            <form action="https://apple-ota.wdf.sap.corp:8443/ota-service/HTML" method="POST">
                                    <input type="hidden" name="title" value="@otaappname@"/>
                                    <input type="hidden" name="bundleIdentifier" value="@otagroupid@"/>
                                    <input type="hidden" name="bundleVersion" value="@otaversion@"/>
                                    <input type="hidden" name="ipaClassifier" value="release"/>
                                    <input type="hidden" name="otaClassifier" value="release-ota"/>
                                    <input type="hidden" id="formReferer" name="Referer" value=""/>
                                    <input type="submit"/>
                            <form>
                    </iframe>

                    <script language="javascript" type="text/javascript">
                            var thisUrl = document.location;
                            var iframe = document.getElementById("iframe");
                            iframe.src=iframe.src+"&Referer="+encodeURIComponent(thisUrl);
                            var formReferer = document.getElementById("formReferer");
                            formReferer.value=encodeURIComponent(thisUrl);
                    </script>

    <br/>
    </body>
    </html>
    """.replace("@otaappname@",otaappname,10)
    html1 =  html.replace("@otaversion@",otaversion,10)
    html1 =  html1.replace("@otagroupid@",otagroupid,10)
    f.write(html1)
    f.close()
    
  def after_DEPLOY(self, build_cfg):
    self.create_redirect_htm()

  def create_redirect_htm(self):
    if self._get_platform() == 'ios' :
        log.info('Creating Redirect HTM file for iOS over the air installation')
        gen_src_dir = os.path.join(self.build_cfg.gen_dir(),"src")
        ios_ota_file = os.path.abspath(os.path.join(self._own_cordova_src_dir(),BUILD_LOCATION[self._get_platform()]['release-ota-htm']%(self.get_cordova_appname())))
        ios_refota_file = os.path.abspath(os.path.join(self._own_cordova_src_dir(),BUILD_LOCATION[self._get_platform()]['release-otaref-htm']%(self.get_cordova_appname())))
        otagroupid = self.get_cordova_groupid()
        otaappname = self.get_cordova_appname()
        otaversion = self.build_cfg.version()
        refgroupid = otagroupid.replace(".","/",10)
        os.environ['HTTP_PROXY']=""
        os.environ['HTTPS_PROXY']=""
        url = self.build_cfg.export_repo() + refgroupid + "/" + otaappname + "/" + otaversion + "/"
        
        try: 
            sock = urllib.urlopen(url)
            htmlsource = sock.read()
            urls = re.findall('(http(.*)-release-ota.htm)\"(.*)',htmlsource, re.M|re.I)
            alist = []
            for url in urls:
                print url[0]
                alist.append(url[0])
            alist.sort(reverse=True)
            otalink = alist[0]
            log.info("otalink : ",otalink)
            #Redirecting to the Nexus OTA
            ref = open(ios_refota_file,'w')
            refhtml = """\
            <html>
                    <head>
                        <meta http-equiv="refresh" content="0; URL=@otalink@">
                        <body>You will be redirected within the next few seconds.<br />In case this does not work click <a href="@otalink@">here</a></body>
            </html>
            """.replace("@otalink@",otalink,10)
            ref.write(refhtml)
            ref.close()
            sock.close()
        except Exception:
            log.warning('Unable to open nexus link',url)
            
        
    if self._get_platform() == 'android' :
        log.info('Creating Redirect HTM file for android over the air installation')
        android_refota_file = os.path.abspath(os.path.join(self._own_cordova_src_dir(),BUILD_LOCATION[self._get_platform()]['release-otaref-htm']%(self.get_cordova_appname())))
        otagroupid = self.get_cordova_groupid()
        otaappname = self.get_cordova_appname()
        otaversion = self.build_cfg.version()
        refgroupid = otagroupid.replace(".","/",10)
        url = self.build_cfg.export_repo() + refgroupid + "/" + otaappname + "/" + otaversion + "/"
        try: 
            sock = urllib.urlopen(url)
            htmlsource = sock.read()
            urls = re.findall('(http(.*).apk)\"(.*)',htmlsource, re.M|re.I)
            alist = []
            for url in urls:
                #print url[0]
                alist.append(url[0])
            alist.sort(reverse=True)
            otalinkandroid = alist[0]
            #Redirecting to the Nexus APK
            ref = open(android_refota_file,'w')
            refhtmlandroid = """\
            <html>
                    <head>
                        <meta http-equiv="refresh" content="0; URL=@otalinkandroid@">
                        <body>You will be redirected within the next few seconds.<br />In case this does not work click <a href="@otalinkandroid@">here</a></body>
            </html>
            """.replace("@otalinkandroid@",otalinkandroid,10)
            ref.write(refhtmlandroid)
            ref.close()
            sock.close()
        except Exception:
            log.warning('Unable to open nexus link',url)
  def _own_dir(self): return os.path.abspath(self.build_cfg.gen_dir())
  def _own_src_dir(self): return os.path.abspath(self.build_cfg.src_dir())
  def _own_cordova_src_dir(self): return os.path.abspath(os.path.join(self.build_cfg.gen_dir(),"src"))
