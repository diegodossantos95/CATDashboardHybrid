import re
from xmake_exceptions import XmakeException
import ConfigParser
import log
import subprocess
from subprocess import call
import os
import shutil
import fnmatch
from os.path import join
import otahtml
import plistlib
import json
import traceback
HTML_TEMPLATE = "<html><head><meta http-equiv=\"refresh\" content=\"0; URL=$LOCATION\"> <body>You will be redirected within the next few seconds.<br /> In case this does not work click <a href=\"$LOCATION\">here</a></body></html>"
class Commons(object):

    def __init__(self,build_cfg, appid_suffix):
        # Initialise default configuration and sdk
        self.configurations              = ["Release"]
        self.sdks	                = ["iphoneos"]
	self.build_cfg       		= build_cfg
	self.build_cfg.tem_dir          = build_cfg.temp_dir()
        self.copied_src_dir  		= join(build_cfg.temp_dir(),'src','xcode')
        self._root           		= build_cfg.component_dir()
        self.importDir		        = build_cfg.import_dir()
        self.prodpass_path	        = build_cfg.tools().prodpassaccess()
        self.outputFolder    		= build_cfg.gen_dir()
        self.j_file	                = build_cfg.deployment_info_log()
        self.appid_suffix	        = appid_suffix
	self.isDebugFlag	        = ""
	self.isExportSrcFlag		= ""
	self.exclude_files		= ""
	# Static variables to identify project types
        self.Application                = "app"
        self.Framework                  = "framework"
        self.Library                    = "lib"
        self.WatchKitApplication        = "watchkit"
	self.workspace_name 	 	= ""
	self.project_name		= ""
	self.isWorkspace		= False
	self.additionalImportFlag	= False

    def copy_src_dir(self):
        """Copies src directory contents to gen/tmp/src directory """
        log.debug('Copying src to ',self.copied_src_dir,' ...')
        if os.path.exists(self.copied_src_dir):
            shutil.rmtree(self.copied_src_dir)
        try:
	    shutil.copytree(join(self._root, 'src', 'xcode'), self.copied_src_dir, True)
        except:
	    log.error("Exception occured while copying to gen/tmp/src")
            log.error(traceback.format_exc())
            raise XmakeException("Exception occured while copying to gen/tmp/src")

    def copy_import_files(self):
    	self.copy_import_files_old() # Temporary to avoid regression from the old plugin version

	if os.path.exists(self.importDir) and os.path.exists(self.build_cfg.temp_dir()):
		log.debug("Import directory path "+self.importDir)
		log.debug("gen/tmp path "+self.build_cfg.temp_dir())
		retCode = call(["ln", "-s", os.path.dirname(self.importDir), self.build_cfg.temp_dir()])
		self.checkError(retCode, "Sym Link has not been created for import directory")
	else:
		log.info("Skipping copying of import files / symbolic link creation.")

    def copy_import_files_old(self):
                """Copies all dependencies headers,libs and frameworks to import/content inside gen/tmp/src """
                importDir = self.build_cfg.import_dir()
                log.debug("copying import dir "+importDir)
                dependencies={"headers":['*.h','*.js'],"libs":['*.a']}
                for configuration in self.configurations:
                        for sdk in self.sdks:
                                word_type = configuration+'-'+sdk
                                if os.path.exists(importDir):

                                        for root, dirnames, filenames in os.walk(importDir):
                                                for dependency in dependencies.keys():
                                                        for extension in dependencies[dependency]:
                                                                for filename in fnmatch.filter(filenames, extension):
                                                                        file=os.path.join(root, filename)
                                                                        log.debug(dependency,file)
                                                                        dependency_Dir = join(self.copied_src_dir,'import','content',dependency,word_type)
                                                                        if not os.path.exists(dependency_Dir):
                                                                                os.makedirs(dependency_Dir)
                                                                        shutil.copy(file,dependency_Dir)


                                                for dirname in fnmatch.filter(dirnames, '*.framework'):
                                                        log.debug("framework file:",dirname)
                                                        framework_file=os.path.join(root, dirname)
                                                        frameworkDir = join(self.copied_src_dir,'import','content','Framework',word_type,dirname)

                                                        if os.path.exists(frameworkDir):
                                                                shutil.rmtree(frameworkDir)
                                                        shutil.copytree(framework_file,frameworkDir)

    def zip_build_results(self, configuration, sdk):
        """    zip build results   """
        if self.project_type == 'framework':
                self.zip_file = self.zip_framework_build(configuration, sdk)
        else:
                self.zip_file = self.zip_archive_files(configuration, sdk)
	if self.isExportSrcFlag == 'True':
		self.zip_src = self.zip_src_files()		

    def zip_src_files(self):
	log.info("Zipping src for export")
	excludeString = ""
	self.exclude_files = "import/\*," + self.exclude_files
	if self.exclude_files == "":
		log.info("No files to exclude while src zipping")
	else:
		for file in self.exclude_files.split(','):
			excludeString += "-x " + "src/xcode" + "/" + file + " "
		excludeString = excludeString.strip()	
		
	zipFileName = self.project_name + '_src' + '.zip'
	try:
		os.chdir(self.build_cfg.tem_dir)
		log.info("Zip src filename: " + zipFileName)
		retCode = os.system("zip -r " + self.outputFolder + "/" + zipFileName + " src/xcode " + excludeString)
	    	self.checkError(retCode, "Error! Zipping src file failed...")
		zipFile=join(self.outputFolder, zipFileName)
        	return zipFile
	finally:
            os.chdir(self._root)

    def zip_archive_files(self, configuration, sdk):
        """ Zips dSYM files of release versions of the frameworks."""
        archiveName       = self.compute_archive_name(self.project_name, configuration, sdk)
        archiveFullName   = archiveName + ".xcarchive" # Need to provide complete file name for zipping
        archiveFolder     = self.compute_archive_path_folder_name(configuration, sdk)
        zipFileName       = archiveName + ".zip"
        log.info('------------- Zipping Archive File ----------------')
        retCode = call(["zip", "-9", "-r", zipFileName, archiveFullName], cwd = archiveFolder)
        self.checkError(retCode, "Error! Zipping archive file for "+ archiveFullName + "-" + configuration + "-" + sdk + " failed...")
        log.info('Zipping archive file ('+ archiveFullName + '-' + configuration + '-' + sdk +') done...(sdk not considered for watchkit)')
        zipFile=join(archiveFolder,zipFileName)
        return zipFile

    def zip_framework_build(self, configuration, sdk):
        """Zips dSYM files of release versions of the frameworks."""
        zipFileName   = self.project_name + "-Build-Artfacts"
        frameworkBuildFolder = 'Build'
        log.info('------------- Zipping Framework Build File ----------------')
        retCode = call(["zip", "-9", "-r", zipFileName, frameworkBuildFolder], cwd=self.outputFolder)
        self.checkError(retCode, "Error! Zipping framework Build file for " + configuration + "-" + sdk + " failed.")
        log.info('Zipping Framework Build file ('+ configuration + '-' + sdk +') done...')
        zipFile=join(self.outputFolder,zipFileName)
        return zipFile

    def unlock_ios_keychain(self):
        """ unlock IOS keychain """
        log.debug('Preparing Pre-requisite for IOS app creation...')
        log.info("prodpasspath "+self.prodpass_path)
        prodpass_cmd_out = '`' + self.prodpass_path +' --credentials-file ' + os.environ['HOME'] + '/.prodpassaccess/credentials.properties --master-file ' + os.environ['HOME'] +'/.prodpassaccess/master.xml get unlock-keychain password`'
        keychain_file = os.environ['HOME'] + '/Library/Keychains/login.keychain'
        log.info('Unlocking iOS keychain...')
        unlockcommand = 'security unlock-keychain -p ' + prodpass_cmd_out + ' ' + keychain_file
        os.system(unlockcommand)
        unlock_return_code = subprocess.call(['security', 'unlock-keychain', '-p', prodpass_cmd_out , keychain_file])
        if not unlock_return_code:
            log.info('SUCCESS - iOS key chain unlock successfully done')
        else:
            log.warning('FAILURE - iOS app signing Unsuccessfully')

    def create_ios_ota_page(self, schemeName, infoPlistPath, artifactId, version, configuration, sdk):
        """creation of an ota installer htm page"""
        try:
            os.chdir(self.copied_src_dir)

            # read the bundle ID from the Info plist and make sure it is hardcoded.
            bundleId = self.read_bundle_id_from_plist(infoPlistPath)
            self.enforce_hardcoded_bundle_id(bundleId)
            self.otaPageFileName = self.outputFolder + "/" + schemeName + '-ota.htm'
            log.info("Creating Over the Air installer page for iOS: " + self.otaPageFileName)

            html = otahtml.OTA_INSTALL_PAGE_HTML
            html = html.replace("@otaappname@",    artifactId,             10)
            html = html.replace("@otaversion@",    version,                10)
            html = html.replace("@otabundleid@",   bundleId,               10)
            html = html.replace("@ipaClassifier@", configuration+"-"+sdk,     10)
            html = html.replace("@otaClassifier@", configuration+"-"+sdk,     10)

            with open(self.otaPageFileName,'w') as otaPageFile:
                otaPageFile.write(html)

            log.info('----------------- done --------------------')
        finally:
            os.chdir(self._root)

    def read_bundle_id_from_plist(self, plistPath):
        """---- Reading bundle ID from Info.plist ----"""
        try:
        	os.chdir(self.copied_src_dir)
            	log.debug("Reading bundle ID from Info.plist ")
                log.debug(' Info.plist path: ' + plistPath)

                infoPlist = plistlib.readPlist(plistPath)
                bundleId  = infoPlist["CFBundleIdentifier"]

                log.debug(' Bundle ID:       ' + bundleId)
                return bundleId
        finally:
            os.chdir(self._root)

    def enforce_hardcoded_bundle_id(self,bundleId):
        """Required by the ota installer to have the bundle id hardcoded in info plist"""
        log.debug('---- Checking if bundle ID is hardcoded ----')
        log.debug('  Current bundle ID is: ' + bundleId)
        matchObject = re.match("([a-z_-]{1}[a-z0-9_-]*(\.[a-z0-9_-]{1}[a-z0-9_-]*)*)$", bundleId, re.IGNORECASE)  # thank you stackoverflow
        if matchObject is None:
            self.checkError(1, "Error! Non-hardcoded Bundle ID. Bundle ID in Info.plist must be hardcoded for OTA deployment to work!")

    #Helper Methods

    def compute_archive_name(self, archiveName, configuration, sdk):
        """ Method that computes the archive name as a concatenation of name, configuration and sdk """
        if self.project_type=='watchkit':
            return archiveName + "-" + configuration
        else:
            return archiveName + "-" + configuration#+ "-" + sdk #Need to include sdk later when multiple sdk support is provided

    def compute_archive_path_folder_name(self, configuration, sdk):
        """Method that computes the archive path folder name """
        outputFolder           = self.outputFolder
        archivesFolderBaseName = "Archives"
        if self.project_type=='watchkit':
            return outputFolder + "/" + archivesFolderBaseName + "-" + configuration
        else:
            return outputFolder + "/" + archivesFolderBaseName + "-" + configuration + "-" + sdk

    def compute_archive_path(self, configuration, sdk, archiveName):
        """ Method that computes the archive path, i.e. the full path to the archvive """
        return self.compute_archive_path_folder_name(configuration, sdk) + "/" + archiveName

    def compute_export_ipa_path(self, configuration, sdk):
        """Computes the path to the export folder that .ipa files are exported to."""
        outputFolder           = self.outputFolder
        archivesFolderBaseName = "Exported-IPAs"
        if self.project_type=='watchkit':
            return outputFolder + "/" + archivesFolderBaseName + "-" + configuration
        else:
            return outputFolder + "/" + archivesFolderBaseName + "-" + configuration + "-" + sdk

    # raises an exception if the return code is not 0.
    # thus it breaks the Xmake build in case commands
    # that were issued as part of the build failed.
    def checkError(self,returnCode, errorMessage):
        if returnCode:
            os.chdir(self._root)
            raise XmakeException(errorMessage)

    def get_xcode_project_info(self):
        """Gets the xcode project information from xcode.cfg"""
        xcode_cfg_location = os.path.join(self._root,'cfg','xcode.cfg')
        if os.path.exists(xcode_cfg_location):
            log.info('Xcode project Config found at: ', xcode_cfg_location)
        else:
            raise XmakeException('Unable to locate xcode.cfg. Aborting build ...')

        config = ConfigParser.RawConfigParser(allow_no_value=True)
        config.read(xcode_cfg_location)
        if config:
            section = 'xcodeproject'
            # Checking for madatory fields in xcode.cfg
            for xcode_info in [ 'group-id', 'scheme-name', 'artifact-id','project-type']:
                if config.has_option(section, xcode_info):
                    exec("self."+xcode_info.replace("-","_")+"=config.get(section,xcode_info)")
                else:
                    self.checkError(1,"No "+xcode_info+" in xcode.cfg...!")

	    # Check for project-name field
	    if config.has_option(section, 'project-name'):
                self.project_name = config.get(section, 'project-name')

	    #Check for workspace field in xcode.cfg
	    if config.has_option(section, 'workspace-name'):
		self.workspace_name = config.get(section, 'workspace-name') 
		self.isWorkspace = True
		if self.project_name == "":
			self.project_name = self.workspace_name
		else:
			self.checkError(1,"project-name and workspace-name cannot be provided together in xcode.cfg ...!")
		
            # Checking for additional fields in xcode.cfg
            if config.has_option(section, 'enable-debug'):
    	    	if config.get(section,'enable-debug').lower() == 'yes':
        		log.info('Debug configuration set...')
              		self.isDebugFlag = 'Debug'
                    	self.configurations.extend(['Debug'])
            # Checking to additional properties to read infoplist properties
            section='infoplist'
    	    if config.has_option(section, 'infoplist-property'):
            	self.infoplist_property = config.get(section, 'infoplist-property')
            else:
        	log.info('There is no additional infoplist property mentioned. If you have multiple targets/extensions, please make sure you have this property in xcode.cfg file')	
	   
    	    # Read import options available
	    section = 'sub-module-import'
	    if config.has_option(section, 'sub-module-dir'):
		log.info('sub-module import found')
		self.additionalImportFlag = True
		self.sub_module_dir = config.get(section,'sub-module-dir')
		
	    # Read export options available           
	    section = 'export'
	    if config.has_option(section, 'export-src'):
                if config.get(section,'export-src').lower() == 'yes':
                    log.info('Exporting of src set...')
                    self.isExportSrcFlag = 'True'
            if config.has_option(section, 'exclude-files'):
		self.exclude_files = config.get(section, 'exclude-files')
        	log.info('There is no additional infoplist property mentioned. If you have multiple targets/extensions, please make sure you have this property in xcode.cfg file')

            # Checking for additional fields in xcode.cfg
            if config.has_option(section, 'enable-debug'):
                if config.get(section,'enable-debug').lower() == 'yes':
                    log.info('Debug configuration set.')
                    self.isDebugFlag = 'Debug'
                    self.configurations.extend(['Debug'])

            if self.project_type=='watchkit':
                section='infoplist'
                for watchkit_info in [ 'infoplist-app-path', 'infoplist-watch-path', 'infoplist-watchext-path' ]:
                    if config.has_option(section, watchkit_info):
                        exec("self."+watchkit_info.replace("-","_") +"=config.get(section,watchkit_info)")
                    else:
                        self.checkError(1,"no "+ watchkit_info +" in xcode.cfg")
        else:
            self.checkError(1,'xcode.cfg does not contain any valid info')

    # Handling import for other dependencies
    def importAdditionalDependencies(self, isExecutingCompanybuild):
	log.info("Performing xmake import for sub-modules")
	# Reading import repo from job context json file
	jobcontext_json_file = ""
	jobcontext_json_file = join(self._root,'.xmake','job_context.json')
	if os.path.exists(jobcontext_json_file):
		with open(jobcontext_json_file) as jsonfile:
			jsondata = jsonfile.read()
			jsondict = json.loads(jsondata)
			import_repo = jsondict['IMPORT_REPO']
	else:
		import_repo = "-I http://nexus.wdf.sap.corp:8081/nexus/content/repositories/build.snapshots/"
	#xmake_run  = join(self._root, '.xmake', 'tools', 'xmake-core', 'src', 'bin', 'xmake')
	xmake_run = 'xmake'
	for dir in self.sub_module_dir.split(','):
		cwd = join(self._root, dir.strip())
		log.info("Import sub-module dir: ", cwd)
		log.info("xmake import call for: ", xmake_run, import_repo, "-s", "-c", "-i", "-B" , "-r", cwd)
		retCode = os.system("xmake -X 0.9.3-33 -s -c -i -B " + import_repo + " -r " + cwd)
		#retCode = call([xmake_run, "-X 0.9.3-33", import_repo, "-s", "-c", "-i", "-B" , "-r ", cwd], shell=True)
		self.checkError(retCode, "xmake import call failed for sub-modules")
		

    def set_new_bundleid_watch(self,num,infoplist_watch_list,bundle_id_watch_list,new_bundle_id_watch_list):
        """This method is used as helper method for change_appid_suffix"""
        log.debug('Bundle Identifier- ', bundle_id_watch_list[num],' found from ', infoplist_watch_list[num])
        plist_command = "/usr/libexec/PlistBuddy", "-x", "-c", "Set :CFBundleIdentifier "+new_bundle_id_watch_list[num], infoplist_watch_list[num]
        retCode = call(plist_command, cwd=self.copied_src_dir)
        log.debug('New bundle id is: ,'+new_bundle_id_watch_list[num])
        self.checkError(retCode, "Error! Unable to set new bundle id in infoplist ")

    def change_appid_suffix(self):
        """Applies '.release' suffix to bundle id in infoplist file for nass builds"""
        log.debug('App Id suffix found: ', self.appid_suffix)

        # To update infoplist preoperties (additional property) for both app and watchkit
	if hasattr(self,'infoplist_property'):
            	for infoplists in self.infoplist_property.split(','):
                        property_values = infoplists.split('|')
                        plist_command = "/usr/libexec/PlistBuddy", "-x", "-c", "Set :" + property_values[1] + " " + property_values[2], property_values[0]
                        log.info("Executing command to update plist: ",plist_command)
                        retCode = call(plist_command, cwd=self.copied_src_dir)
                        self.checkError(retCode, "Error! Unable to set property " + property_values[1] + " in infoplist: " + property_values[0])

        if self.project_type == 'watchkit':
            infoplist_watch_list = [self.infoplist_app_path , self.infoplist_watch_path , self.infoplist_watchext_path]
            bundle_id_watch_list = list(map(self.read_bundle_id_from_plist , infoplist_watch_list))
            if '' in bundle_id_watch_list :
                log.error('Error finding Bundle Identifier from Info.plist file')
            new_bundle_id_watch_list=[bundle_id_watch_list[0].strip()+self.appid_suffix.strip()]
            new_bundle_id_watch_list.append(new_bundle_id_watch_list[0]+'.watchkitapp'.strip())
            new_bundle_id_watch_list.append(new_bundle_id_watch_list[1]+'.watchkitextension'.strip())
            for num in range(3):
                self.set_new_bundleid_watch(num,infoplist_watch_list,bundle_id_watch_list,new_bundle_id_watch_list)
            #Fixing the broken links after appending appid suffix
            plist_command = "/usr/libexec/PlistBuddy", "-x", "-c", "Set :NSExtension:NSExtensionAttributes:WKAppBundleIdentifier " +new_bundle_id_watch_list[1], infoplist_watch_list[2]
            retCode = call(plist_command, cwd=self.copied_src_dir)

            plist_command = "/usr/libexec/PlistBuddy", "-x", "-c", "Set :WKCompanionAppBundleIdentifier " +new_bundle_id_watch_list[0], infoplist_watch_list[1]
            retCode = call(plist_command, cwd=self.copied_src_dir)
        else:
            info_plist_file = self.get_infoplist_file()
            bundle_id = self.read_bundle_id_from_plist(info_plist_file)
            if not bundle_id:
                log.error('Error finding Bundle Identifier from Info.plist')
            log.debug('Bundle Identifier found: ', bundle_id)
            new_bundle_id = bundle_id.strip()+self.appid_suffix.strip()
            log.debug('New Bundle ID: ', new_bundle_id)
            plist_command = "/usr/libexec/PlistBuddy", "-x", "-c", "Set :CFBundleIdentifier "+new_bundle_id, info_plist_file
            retCode = call(plist_command, cwd=self.copied_src_dir)
            self.checkError(retCode, "Error! Unable to set new bundle id in infoplist")


    def update_version_infoplist(self, version):
        if self.project_type == 'watchkit':
            infoplist_watch_list = [self.infoplist_app_path , self.infoplist_watch_path , self.infoplist_watchext_path]
            for plist in infoplist_watch_list:
                # Updating CFBunfleVersion with version from version.txt
                plist_command = "/usr/libexec/PlistBuddy", "-x", "-c", "Set :CFBundleVersion " + version, plist
                retCode = call(plist_command, cwd=self.copied_src_dir)
                self.checkError(retCode, "Error! Unable to set CFBundleVersion in infoplist: " + plist)
                # Updating CFBundleShortVersionString with version from version.txt
                plist_command = "/usr/libexec/PlistBuddy", "-x", "-c", "Set :CFBundleShortVersionString " + version, plist
                retCode = call(plist_command, cwd=self.copied_src_dir)
                self.checkError(retCode, "Error! Unable to set CFBundleShortVersionString in infoplist: " + plist)
	
	if self.isWorkspace:
	    info_plist_file = self.get_infoplist_file()
	else:
	    # Applicable for App Type only
            info_plist_file = self.get_infoplist_file()
            # Updating CFBunfleVersion with version from version.txt
            plist_command = "/usr/libexec/PlistBuddy", "-x", "-c", "Set :CFBundleVersion " + version, info_plist_file
            retCode = call(plist_command, cwd=self.copied_src_dir)
            self.checkError(retCode, "Error! Unable to set CFBundleVersion in infoplist: " + info_plist_file)
            # Updating CFBundleShortVersionString with version from version.txt
            plist_command = "/usr/libexec/PlistBuddy", "-x", "-c", "Set :CFBundleShortVersionString " + version, info_plist_file
            retCode = call(plist_command, cwd=self.copied_src_dir)
            self.checkError(retCode, "Error! Unable to set CFBundleShortVersionString in infoplist: " + info_plist_file)

    def get_infoplist_file(self): #Function to read infoplist path from Xcode build settings
        """ Function to read infoplist path from Xcode build settings """
        try:                        
	    os.chdir(self.copied_src_dir)
            log.debug('Working directory is now: ',os.getcwd())
	    if self.isWorkspace:
                infoplistFile  = subprocess.check_output('xcodebuild clean -scheme ' + "'" + self.scheme_name + "'" + ' -showBuildSettings | grep PRODUCT_SETTINGS_PATH', shell=True)
                log.info('infoplist found as: ', infoplistFile.split("=")[1].strip())
                return infoplistFile.split("=")[1].strip()
	    else:
		log.debug('Working directory is now: ',os.getcwd())
                returnString  = subprocess.check_output('xcodebuild clean -scheme ' + "'" + self.scheme_name + "'" + ' -showBuildSettings | grep INFOPLIST_FILE', shell=True)
                log.info('infoplist found: ',returnString.split("=")[1].strip())
                return returnString.split("=")[1].strip()
        except:
            raise XmakeException("Build Failed. Unable to read infoplist file details from Xcode build settings")
        finally:
            os.chdir(self._root)

    def createSuccesfulArtifactFolder(self):
        log.debug('Found deployment_info_log file',self.j_file)
        sepratorForGA = '_abcz_'
        dictGA = {}
        dictURL = {}
        log.debug('Info:Parsing the json file',self.j_file)
        with open(self.j_file) as f:
            j_obj = json.load(f)
            urlValues = j_obj['deploymentInfos']
            for rs in urlValues:
                urlFromJson = rs['URL']
                j_groupId = rs['artifact']['groupId']
                j_artifactId = rs['artifact']['artifactId']
                keyForGA = j_groupId + sepratorForGA + j_artifactId
                dictGA[keyForGA] = 0
                dictURL[urlFromJson] = keyForGA

        for keyURL in dictURL.iterkeys():
            artifact_groupId = dictURL[keyURL].split(sepratorForGA)[0]
            artifact_artifactId = dictURL[keyURL].split(sepratorForGA)[1]
            artifactFolderPath = self.create_artifactREdirectFolderStructure(artifact_groupId, artifact_artifactId)
            htmlurl = HTML_TEMPLATE.replace("$LOCATION",keyURL)

            if keyURL.endswith('.htm'): #temporary condn to handle -ota
                tempVar = keyURL.split('.htm')[0]
                keyURL = tempVar.strip()+'-ota.htm'
            artifactFileFullName = keyURL.rpartition('/')[2]
            artifactName = self.getRedirectHtmlFilename(artifactFileFullName, artifact_artifactId)
            self.createHTMLFileforArtifacts(artifactName, artifactFolderPath, htmlurl)

    def getNthIndexFromBack(self, string, searchString, countFromBack):
        if (countFromBack <= 0):
            return -1
        idx = len(string)
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
            nthElement = 2
        elif artifactFileName.endswith("-AppStoreMetaData.zip"):
            nthElement = 1
        elif (artifactFileName.endswith("-app.dSYM.zip")):
            nthElement = 3
        elif (artifactFileName.endswith("-app.zip")):
            nthElement = 3
        elif (artifactFileName.endswith(".ipa")):
            nthElement = 1
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
        if os.path.exists(self.outputFolder):
            artifact_dir = r"artifactsRedirect/artifacts/"
            artifactFolder = os.path.join(self.outputFolder, artifact_dir, artifact_groupId, artifact_artifactId)
            if not os.path.exists(artifactFolder):
                os.makedirs(artifactFolder)
            return artifactFolder

    def validateVersion(self, version):
	if version.count('.') > 2:
        	self.checkError(1, "Invalid version in version.txt. Please check format supported by Apple before releasing ...")
        # Here we are not doing any SNAPHOT validation as this is already taken care at xmake frmaework level. Plugin need'nt handle it.
        if "SNAPSHOT" in version.upper():
        	versionString = version.split('-')
        	matchObject = re.match("(^[0-9.]+$)", versionString[0])
        else:
        	matchObject = re.match("(^[0-9.]+$)", version)
        if matchObject is None:
        	self.checkError(1, "Invalid version in version.txt. Please check format supported by Apple before releasing ...")
