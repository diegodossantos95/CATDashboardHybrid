import os
import spi
import log
import re
import json
from subprocess import call
from os.path import join
import sys
from copy import deepcopy
# Importing common Functionality
sys.path.append(join(os.path.dirname(os.path.realpath(__file__)),'template')) # Need to change this folder to common
sys.path.append(join(os.path.dirname(os.path.realpath(__file__)),'commons'))
from commons import Commons

class BuildPlugin(spi.BuildPlugin):
    
    def __init__(self, build_cfg):
        # Defaults set to variables used 
        self.build_cfg                  = build_cfg
        self.version                    = self.build_cfg.base_version()
        self.outputFolder               = self.build_cfg.gen_dir()
        self.cfg_path                   = self.build_cfg.cfg_dir()
        self.skipVersionUpdateFlag	= False
	self._root                      = self.build_cfg.component_dir()
        self.appid_suffix               = '.release'
        self.artifact_suffix_release    = '_release'
        self.isExecutingCompanybuild    = False
        self.isExecutingEnterprisebuild = False
        self.isExecutingDevelopmentbuild= False
        self.isExecutingLocalbuild	= False
        self.home			= os.getenv('HOME')
        
        # Set template folder path
	self.template_path	        = join(os.path.dirname(os.path.realpath(__file__)), 'template')
	self.export_path                = join(self.template_path, 'export')
        # Pass required variable to the Commons class in common/commons.py
        self.common                     = Commons(self.build_cfg, self.appid_suffix)
        self.centralSigingConfigFolder  = join(self.cfg_path, "central-signing")  # the folder containing the central signing overrides
        self.localSigingConfigFolder    = join(self.cfg_path, "local-signing")    # the folder containing the central signing overrides
        self.signingDefaultsFolder      = join(self.template_path, "signing-defaults")
	
        # meaningful defaults for NAAS
        self.defaultNaasSigningConfig              = join(self.signingDefaultsFolder, "NAASSigning.xcconfig")
        self.defaultNaasSigningExportOptions       = join(self.signingDefaultsFolder, "NAASSigningExportOptions.plist")
        # meaningful signing defaults for production
        self.defaultProductionSigningConfig        = join(self.signingDefaultsFolder, "ProductionSigning.xcconfig")
        self.defaultProductionSigningExportOptions = join(self.signingDefaultsFolder, "ProductionSigningExportOptions.plist") 
    	# Set defaults from build args
    	if self.build_cfg.build_args():
            if "build-profile=comp" in self.build_cfg.build_args():
                self.isExecutingCompanybuild	   = True
            if "build-profile=ent" in self.build_cfg.build_args():
                self.isExecutingEnterprisebuild	   = True
            if "build-profile=dev" in self.build_cfg.build_args():
                self.isExecutingDevelopmentbuild   = True
        else:
            self.isExecutingLocalbuild	   = True
	# Set value for version update
	if os.getenv('SKIP_VERSION_UPDATE') == "true":
		self.skipVersionUpdateFlag = True
	# Read info of project from cfg/xcode.cfg
        self.common.get_xcode_project_info()
    
    def after_PROMOTE(self,build_cfg):
	jobcontext_json_file = ""
	jsondict = None
	jobcontext_json_file = join(self._root,'.xmake','job_context.json')
	if os.path.exists(jobcontext_json_file):
	    with open(jobcontext_json_file) as jsonfile:
		jsondata = jsonfile.read()
		jsondict = json.loads(jsondata)	        
        releaseNexusRepo="https://nexus.wdf.sap.corp:8443/nexus/content/repositories/deploy.releases"
        devNexusRepo="https://nexus.wdf.sap.corp:8443/nexus/content/repositories/deploy.milestones"
	if jsondict and 'MODE' in jsondict:
	    if jsondict['MODE']=='promote' and jsondict['V_TEMPLATE_TYPE']=="OD-common-staging" or jsondict['MODE']=='stage_and_promote' and jsondict['V_TEMPLATE_TYPE']=="OD-common-staging" and os.path.exists(join(self._root,'.xmake','staging_info','staging_closed.txt')):
	        buildquality = jsondict['build_quality']
	        if 'VERSION_EXTENSION' in jsondict:
	            self.version=self.version+"-"+jsondict['VERSION_EXTENSION']
	        if buildquality=="release":
	            nexusPromotedReleaseRepo=os.path.join(releaseNexusRepo,self.common.group_id.replace('.','/'),self.common.artifact_id+'_release',self.version)
	            log.info('Company Release Promoted repository link ',nexusPromotedReleaseRepo)
	        if buildquality=="milestone":
	            nexusPromotedDevRepo=os.path.join(devNexusRepo,self.common.group_id.replace('.','/'),self.common.artifact_id,self.version)
	            log.info('Promoted Milestone Nexus repostitory link',nexusPromotedDevRepo)

    def updateProvisioningProfiles(self):
        self.Provisioning_profile_slave_path     = self.home+"/Library/MobileDevice/Provisioning\ Profiles"
	if os.path.exists(self.centralSigingConfigFolder):
	    for file in os.listdir(self.centralSigingConfigFolder):
	        if file.endswith(".mobileprovision"):
		    log.debug("Creating symbolic links to dedicated provisioning profile "+file)
		    retcode=os.system("ln -sf "+self.centralSigingConfigFolder+"/"+file+" "+self.Provisioning_profile_slave_path+"/"+self.common.artifact_id+self.common.project_name+file)
            	    self.common.checkError(retcode, "Sym Link has not been created for provisioning profiles")   
    
            	
    def initializeSigning(self):
        if self.isExecutingCompanybuild: # Check for company builds
	        self.signingConfig        = os.path.join(self.centralSigingConfigFolder, "NAASSigning.xcconfig")
	        self.signingExportOptions = os.path.join(self.centralSigingConfigFolder, "NAASSigningExportOptions.plist")
	        if not os.path.exists(self.signingConfig):
	        	# Temporary so that it doesnt create a regression
	        	if os.path.exists(os.path.join(self._root, 'cfg', 'CentralSigningNaas.xcconfig')):
	        		self.signingConfig = os.path.join(self._root, 'cfg', 'CentralSigningNaas.xcconfig')
	        	else:
	                	self.common.checkError(1,"Error! Signing.xcconfig file required for NAAS xmake xcode builds. Place one here: " + self.signingConfig)
	        if not os.path.exists(self.signingExportOptions):
	                self.signingExportOptions = self.defaultNaasSigningExportOptions
	                
        elif self.isExecutingEnterprisebuild or self.isExecutingDevelopmentbuild: 
                log.debug("Running on Central ent/dev builds")
                self.signingConfig = join(self.centralSigingConfigFolder, "ProductionSigning.xcconfig")
                self.signingExportOptions = join(self.centralSigingConfigFolder, "ProductionSigningExportOptions.plist")
                if not os.path.exists(self.signingConfig):
                	# Temporary so that it doesnt create a regression
                	if os.path.exists(os.path.join(self._root, 'cfg', 'CentralSigning.xcconfig')):
	        		self.signingConfig = os.path.join(self._root, 'cfg', 'CentralSigning.xcconfig')
	        	else:
	        		self.signingConfig = self.defaultProductionSigningConfig
                if not os.path.exists(self.signingExportOptions):
                        self.signingExportOptions = self.defaultProductionSigningExportOptions

        elif self.isExecutingLocalbuild:
            log.debug("Running on local machine builds")
            # the local signing xcconfig to override signing settings.
            self.signingConfig        = join(self.localSigingConfigFolder, "Signing.xcconfig")
            # the local signing export options plist to override signing
            self.signingExportOptions = join(self.localSigingConfigFolder, "SigningExportOptions.plist")

            if not os.path.exists(self.signingConfig):
                log.info("Signing.xcconfig file required for local xmake xcode builds,else it will be taken from buildsettings...!")
            if not os.path.exists(self.signingExportOptions):
                log.info("SigningExportOptions.plist file required for local xmake xcode builds, if not it will be taken from buildsettings...!")
        else:
        	self.common.checkError(1, "Unknown project type! Exiting ...!")	
                       
    def run(self):
	# branch name validation
	#self.gitBranchValidation()	
        if self.common.additionalImportFlag:
            self.common.importAdditionalDependencies(self.isExecutingCompanybuild)
    	# Copying src to gen/tmp/src folder as per the Golden Rules of xMake
        self.common.copy_src_dir()  
        # To create sym Links for import dir
        self.common.copy_import_files()
	# To check or validate version provided.it is required to update version in plist
	self.common.validateVersion(self.version)
        #Copy dedicated provisioning profiles
    	if self.isExecutingEnterprisebuild or self.isExecutingDevelopmentbuild or self.isExecutingLocalbuild:
            self.updateProvisioningProfiles()
        # Call build functions on basis of project types
        if self.common.project_type == self.common.Application:
            self.initializeSigning()
            self.runApplicationBuild()
        elif self.common.project_type == self.common.Framework:
            self.runFrameworkBuild()
        elif self.common.project_type == self.common.Library:
            self.runLibraryBuild()
        elif self.common.project_type == self.common.WatchKitApplication:
            self.initializeSigning()
            self.runWatchKitApplicationBuild()
        # Preparing export.ads for respective project type
        self.prepare_export(self.common.project_type)  
    
    def runApplicationBuild(self):
        log.info("---------------------Running Application build---------------------")
        # Function call to unlock keychain access before signing
        self.common.unlock_ios_keychain()
        # To update the version in CFBundleVersion and CFBundleShortVersionString 
        if not self.skipVersionUpdateFlag:
	    log.info("Updating version field in infoplist ...")
       	    self.common.update_version_infoplist(self.version)
        if self.isExecutingCompanybuild:
            self.common.change_appid_suffix() # Function to append appid suffix
        self.xcrunBinary    = "xcrun"
        self.xcodeBinary    = "xcodebuild"
        self.xcodebuildCommand_list = [self.xcrunBinary,
                                           self.xcodeBinary,
                                           "-scheme",          self.common.scheme_name,
                                           "-derivedDataPath", self.outputFolder,
                                           "-xcconfig",        self.signingConfig,
                                            ]
        if self.common.isWorkspace:
		self.xcodebuildCommand_list.extend(["-workspace", self.common.workspace_name+".xcworkspace"])
	else:
		self.xcodebuildCommand_list.extend(["-project", self.common.project_name+".xcodeproj"])

	xcodebuildCommand = deepcopy(self.xcodebuildCommand_list) 
        for configuration in self.common.configurations:
            for sdk in self.common.sdks:
                ################################### Xcode Clean ##################################
                xcodebuildCommand.extend(["-sdk", sdk,
                                          "-configuration",   configuration,
                                          "clean"])
                log.info('--------- Executing XCode Clean ---------')
                log.info(' CONFIGURATION: ', configuration)
                log.info(' SDK:           ', sdk)
                log.info(' xcodebuildCommand:           ', xcodebuildCommand)
                log.info('-----------------------------------------')
                retCode = call(xcodebuildCommand, cwd=self.common.copied_src_dir)
                self.common.checkError(retCode, "Error! Xcode CLEAN failed.")
                log.info('----------------- done --------------------')
                ################################### Xcode Clean ##################################
        
                ################################### Xcode Archive ################################
                """archiving application sources for later export into an .ipa file"""
                log.info( 'Archiving application sources...' )
                archiveName = self.common.compute_archive_name(self.common.project_name, configuration, sdk)
                archivePath = self.common.compute_archive_path(configuration, sdk, archiveName)
                xcodebuildCommand = deepcopy(self.xcodebuildCommand_list)
                xcodebuildCommand.extend(["-sdk", sdk,
                                          "-configuration",   configuration,
                                          "-archivePath",     archivePath,
                                          "ENABLE_BITCODE=NO",
                                          "archive"])    
                log.info('--------- Executing xcodebuild archive ---------')
                log.info(' CONFIGURATION: ', configuration)
                log.info(' SDK:           ', sdk)
                log.info(' xcodebuildCommand:           ', xcodebuildCommand)
                retCode = call(xcodebuildCommand, cwd=self.common.copied_src_dir)
                self.common.checkError(retCode, "Error! Archiving of Application sources failed.")
                log.info('----------------- done --------------------')
                ################################### Xcode Archive #################################
                
                ################################### Xcode Export ##################################
                """exports the archived sources into an .ipa file for distribution."""
                log.info( 'Exporting application archive...' )
                archivePath        = self.common.compute_archive_path(configuration, sdk, archiveName) + ".xcarchive"
                exportPath         = self.common.compute_export_ipa_path(configuration, sdk)
                exportOptionsPlist = self.signingExportOptions
                
                xcodebuildCommand = [
                                     self.xcrunBinary,
                                     self.xcodeBinary,
                                     "-exportArchive",
                                     "-archivePath",        archivePath,
                                     "-exportOptionsPlist", exportOptionsPlist,
                                     "-exportPath",         exportPath
                                     ]
                                     
                log.info('--------- Executing xcodebuild export ---------')
                log.info(' xcodebuildCommand:           ', xcodebuildCommand)
                retCode = call(xcodebuildCommand, cwd=self.common.copied_src_dir)
                self.common.checkError(retCode, "Error! Exporting of Application archive failed.")
                log.info('----------------- done --------------------')
                ################################### Xcode Export ##################################
                
                # Function call to zip build results (xcarchives)
                self.common.zip_build_results(configuration, sdk)
                # Function call to create OTA Page.
                self.common.create_ios_ota_page(self.common.scheme_name, self.common.get_infoplist_file(), self.common.project_name, self.version, configuration,sdk)
        return True

    def runFrameworkBuild(self):
        log.info("---------------------Running Framework build----------------------")
        # Function call to unlock keychain access before signing
        self.xcrunBinary    = "xcrun"
        self.xcodeBinary    = "xcodebuild"
        self.xcodebuildCommand_list = [self.xcrunBinary,
                                           self.xcodeBinary,
                                           "-scheme",          self.common.scheme_name,
                                           "-derivedDataPath", self.outputFolder,
                                            ]
	if self.common.isWorkspace:
                self.xcodebuildCommand_list.extend(["-workspace", self.common.workspace_name+".xcworkspace"])
        else:
                self.xcodebuildCommand_list.extend(["-project", self.common.project_name+".xcodeproj"])

        for configuration in self.common.configurations:
            for sdk in self.common.sdks:
                ################################### Xcode Clean ##################################
                xcodebuildCommand = deepcopy(self.xcodebuildCommand_list)
                xcodebuildCommand.extend(["-sdk", sdk,
                                          "-configuration",   configuration,
                                          "clean"])
                log.info('--------- Executing XCode Clean ---------')
                log.info(' CONFIGURATION: ', configuration)
                log.info(' SDK:           ', sdk)
                log.info(' xcodebuildCommand:           ', xcodebuildCommand)
                log.info('-----------------------------------------')
                retCode = call(xcodebuildCommand, cwd=self.common.copied_src_dir)
                self.common.checkError(retCode, "Error! Xcode CLEAN failed.")
                log.info('----------------- done --------------------')
                ################################### Xcode Clean ##################################
        
                ################################### Xcode Build ################################
                """archiving application sources for later export into an .ipa file"""
                log.info( 'Building application sources...' )
                xcodebuildCommand = deepcopy(self.xcodebuildCommand_list)
                xcodebuildCommand.extend(["-sdk", sdk,
                                          "-configuration",   configuration,
                                          "ONLY_ACTIVE_ARCH=NO",
                                          "VALID_ARCHS=armv7 armv7s arm64",])    
                log.info('--------- Executing xcodebuild command ---------')
                log.info(' CONFIGURATION: ', configuration)
                log.info(' SDK:           ', sdk)
                log.info(' xcodebuildCommand:           ', xcodebuildCommand)
                retCode = call(xcodebuildCommand, cwd=self.common.copied_src_dir)
                self.common.checkError(retCode, "Error! Archiving of Framework sources failed.")
                log.info('----------------- done --------------------')
                ################################### Xcode Build #################################
                
        # Function call to zip build results 
        self.common.zip_build_results(configuration, sdk)
                
        return True
        
    def runLibraryBuild(self):
        log.info("---------------------Running Library build----------------------")
        # Function call to unlock keychain access before signing
        self.xcrunBinary    = "xcrun"
        self.xcodeBinary    = "xcodebuild"
        self.xcodebuildCommand_list = [self.xcrunBinary,
                                           self.xcodeBinary,
                                           "-scheme",          self.common.scheme_name,
                                           "-derivedDataPath", self.outputFolder,
                                            ]
	if self.common.isWorkspace:
                self.xcodebuildCommand_list.extend(["-workspace", self.common.workspace_name+".xcworkspace"])
        else:
                self.xcodebuildCommand_list.extend(["-project", self.common.project_name+".xcodeproj"])
 
        for configuration in self.common.configurations:
            for sdk in self.common.sdks:
                ################################### Xcode Clean ##################################
                xcodebuildCommand = deepcopy(self.xcodebuildCommand_list)
                xcodebuildCommand.extend(["-sdk", sdk,
                                          "-configuration",   configuration,
                                          "clean"])
                log.info('--------- Executing XCode Clean ---------')
                log.info(' CONFIGURATION: ', configuration)
                log.info(' SDK:           ', sdk)
                log.info(' xcodebuildCommand:           ', xcodebuildCommand)
                log.info('-----------------------------------------')
                retCode = call(xcodebuildCommand, cwd=self.common.copied_src_dir)
                self.common.checkError(retCode, "Error! Xcode CLEAN failed.")
                log.info('----------------- done --------------------')
                ################################### Xcode Clean ##################################
        
                ################################### Xcode Archive ################################
                """archiving application sources for later export into an .ipa file"""
                log.info( 'Archiving application sources...' )
                archiveName = self.common.compute_archive_name(self.common.project_name, configuration, sdk)
                archivePath = self.common.compute_archive_path(configuration, sdk, archiveName)
                xcodebuildCommand = deepcopy(self.xcodebuildCommand_list)
                xcodebuildCommand.extend(["-sdk", sdk,
                                          "-configuration",   configuration,
                                          "-archivePath",     archivePath,
                                          "ONLY_ACTIVE_ARCH=NO",
                                          "VALID_ARCHS=armv7 armv7s arm64",
                                          'RUN_CLANG_STATIC_ANALYZER=NO',
                                          "archive",
                                          "SKIP_INSTALL=NO"])    
                log.info('--------- Executing xcodebuild archive ---------')
                log.info(' CONFIGURATION: ', configuration)
                log.info(' SDK:           ', sdk)
                log.info(' xcodebuildCommand:           ', xcodebuildCommand)
                retCode = call(xcodebuildCommand, cwd=self.common.copied_src_dir)
                self.common.checkError(retCode, "Error! Archiving of Library sources failed.")
                log.info('----------------- done --------------------')
                ################################### Xcode Archive #################################
        
                # Function call to zip build results (xcarchives)
                self.common.zip_build_results(configuration, sdk)
        return True

    def runWatchKitApplicationBuild(self):
        log.info("---------------------Running WatchKit Application build---------------------")
        # Function call to unlock keychain access before signing
        self.common.unlock_ios_keychain()
        # To update the version in CFBundleVersion and CFBundleShortVersionString 
        if not self.skipVersionUpdateFlag:
      	    self.common.update_version_infoplist(self.version)
                
        if self.isExecutingCompanybuild :
            self.common.change_appid_suffix() # Function to append appid suffix
        self.xcrunBinary    = "xcrun"
        self.xcodeBinary    = "xcodebuild"
        self.xcodebuildCommand_list = [self.xcrunBinary,
                                           self.xcodeBinary,
                                           "-scheme",          self.common.scheme_name,
                                           "-derivedDataPath", self.outputFolder,
                                           "-xcconfig",        self.signingConfig,
                                            ]
	if self.common.isWorkspace:
                self.xcodebuildCommand_list.extend(["-workspace", self.common.workspace_name+".xcworkspace"])
        else:
                self.xcodebuildCommand_list.extend(["-project", self.common.project_name+".xcodeproj"])

        for configuration in self.common.configurations:
            xcodebuildCommand = deepcopy(self.xcodebuildCommand_list)
            for sdk in self.common.sdks:
                ################################### Xcode Clean ##################################
                xcodebuildCommand.extend(["-configuration",   configuration,
                                          "clean"])
                log.info('--------- Executing XCode Clean ---------')
                log.info(' CONFIGURATION: ', configuration)
                log.info(' xcodebuildCommand:           ', xcodebuildCommand)
                log.info('-----------------------------------------')
                retCode = call(xcodebuildCommand, cwd=self.common.copied_src_dir)
                self.common.checkError(retCode, "Error! Xcode CLEAN failed.")
                log.info('----------------- done --------------------')
                ################################### Xcode Clean ##################################
        
                ################################### Xcode Archive ################################
                """archiving application sources for later export into an .ipa file"""
                log.info( 'Archiving application sources...' )
                archiveName = self.common.compute_archive_name(self.common.project_name, configuration, sdk)
                archivePath = self.common.compute_archive_path(configuration, sdk, archiveName)
                xcodebuildCommand = deepcopy(self.xcodebuildCommand_list)
                xcodebuildCommand.extend(["-configuration",   configuration,
                                          "-archivePath",     archivePath,
                                          "archive"])    
                log.info('--------- Executing xcodebuild archive ---------')
                log.info(' CONFIGURATION: ', configuration)
                log.info(' xcodebuildCommand:           ', xcodebuildCommand)
                retCode = call(xcodebuildCommand, cwd=self.common.copied_src_dir)
                self.common.checkError(retCode, "Error! Archiving of Application sources failed.")
                log.info('----------------- done --------------------')
                ################################### Xcode Archive #################################
                
                ################################### Xcode Export ##################################
                """exports the archived sources into an .ipa file for distribution."""
                log.info( 'Exporting application archive...' )
                archivePath        = self.common.compute_archive_path(configuration, sdk, archiveName) + ".xcarchive"
                exportPath         = self.common.compute_export_ipa_path(configuration, sdk)
                exportOptionsPlist = self.signingExportOptions
                
                xcodebuildCommand = [
                                     self.xcrunBinary,
                                     self.xcodeBinary,
                                     "-exportArchive",
                                     "-archivePath",        archivePath,
                                     "-exportOptionsPlist", exportOptionsPlist,
                                     "-exportPath",         exportPath
                                     ]
                                     
                log.info('--------- Executing xcodebuild export ---------')
                log.info(' CONFIGURATION: ', configuration)
                log.info(' SDK:           ', sdk)
                log.info(' xcodebuildCommand:           ', xcodebuildCommand)
                retCode = call(xcodebuildCommand, cwd=self.common.copied_src_dir)
                self.common.checkError(retCode, "Error! Exporting of WatchKit Application archive failed.")
                log.info('----------------- done --------------------')
                ################################### Xcode Export ##################################
                
                # Function call to zip build results (xcarchives)
                self.common.zip_build_results(configuration, sdk)
                
                # Function call to create OTA Page.
                self.common.create_ios_ota_page(self.common.scheme_name, self.common.get_infoplist_file(), self.common.project_name, self.version, configuration,sdk)
        return True
       
    def deploy_variables(self):
    	if self.isExecutingCompanybuild: # This is applicable for app and watchkit only as library and framework compabny builds are not triggered
            self.common.artifact_id = self.common.artifact_id + self.artifact_suffix_release    
        return {            
                'groupId'       : self.common.group_id,
                'artifactId'    : self.common.artifact_id,
                'schemeName'    : self.common.scheme_name,
                'DebugFlag'     : self.common.isDebugFlag,
                'projectName'   : self.common.project_name,
		'ExportSrcFlag' : self.common.isExportSrcFlag,
		}
        
    def prepare_export(self, project_type):
        # Set the default export script
        if not os.path.exists(self.build_cfg.export_script()):
            ads = join(self.export_path, project_type + '_export.ads')
            log.debug("Setting the default export script to: "+ads)
            self.build_cfg.set_export_script(ads)
            
    def after_DEPLOY(self, build_cfg):
        if (os.path.exists(self.build_cfg.deployment_info_log())):
            log.info('deployment info log found. Creating last successful artifacts ...')
            self.common.createSuccesfulArtifactFolder()
        else:
            log.info('No deployment Info log found')

    def gitBranchValidation(self):
	if os.getenv('build_quality') and os.getenv('GIT_BRANCH'):
	    buildType = os.getenv('build_quality')
	    branchName = os.getenv('GIT_BRANCH')
	    log.info('git Branch name: ', branchName)
	    log.info('Build Type: ', buildType)
	    if buildType == 'release':
	    	if 'fa/rel' in branchName:
		    log.info('git branch validation against job type success')
		else:
		    self.common.checkError(1, 'git branch ' + branchName + ' not supported for this job type')
