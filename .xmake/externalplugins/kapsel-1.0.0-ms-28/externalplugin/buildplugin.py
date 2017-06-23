import os
import subprocess
import log
import spi
import fileinput
import sys
import zipfile
import re
import xml.dom.minidom as minidom
from xmake_exceptions import XmakeException

class BuildPlugin(spi.BuildPlugin):

    def __init__(self, build_cfg):
        spi.BuildPlugin.__init__(self, build_cfg)

        self._build_plugin_path = os.path.dirname(os.path.realpath(__file__))

        # Maven client used for Android signing
        self._maven_client_toolid = 'com.sap.prd.codesign.mavenclient:com.sap.prd.codesign.mavenclient.dist.cli'
        self._maven_client_version = '1.0.0'

        # Cordova
        self._cordova_cli_version = '7.0.1'
        self._cordova_build_type = 'release'
        self._cordova_browserify = False

        # XCode config files
        self._xcode_xcconfig_enterprise = None
        self._xcode_xcconfig_naas = None
        self._xcode_xcconfig_local = None

        if self.build_cfg.variant_info() is not None and 'cordova_platform' in self.build_cfg.variant_info():
            self._cordova_platform = self.build_cfg.variant_info()['cordova_platform']
        else:
            log.info('No Cordova platform provided using default for system')
            self._cordova_platform = self._default_cordova_platform()

        if self._cordova_platform not in ['android', 'ios']:
            raise XmakeException('Platform {0} is not supported'.format(platform))

        # Kapsel
        self._kapsel_group = 'com.sap.kapsel.plugins.dist'
        self._kapsel_version = '3.15.0'

        # Runtime specific variables
        if sys.platform == "linux" or sys.platform == "linux2":
            self._java_classifier = 'linux-x64'
            self._node_classifier = 'linux-x64'
            self._android_sdk_platform_tools_artifactid = 'platform-tools-linux'
            self._android_sdk_build_tools_artifactid = 'build-tools-linux'
        elif sys.platform == "darwin":
            self._java_classifier = 'macosx-x64'
            self._node_classifier = 'darwin-x64'
            self._android_sdk_platform_tools_artifactid = 'platform-tools-macosx'
            self._android_sdk_build_tools_artifactid = 'build-tools-macosx'
        elif _platform == "win32":
            self._java_classifier = 'windows-x64'
            self._node_classifier = 'x64'
            self._android_sdk_platform_tools_artifactid = 'platform-tools-windows'
            self._android_sdk_build_tools_artifactid = 'build-tools-windows'
        else:
            raise XmakeException('Unsupported runtime: ' + self.build_cfg.runtime())

        # nodeJS
        self._nodejs_group_artifact = 'org.nodejs.download.node:node'
        self._nodejs_version = '4.3.1'

        # Java
        self._java_toolid = 'com.oracle.download.java:jdk'
        self._java_version = '1.8.0_66-sap-01'

        # Gradle
        self._gradle_toolid = 'org.gradle.download.gradle:gradle'
        self._gradle_version = '3.3'

        # LeanDI group for Android SDK uploads
        self._android_group = 'com.google.download.android'

        # Android SDK Tools
        self._android_sdk_tools_toolid = self._android_group + ':tools'
        self._android_sdk_tools_version = 'r25.1.7'

        # Android SDK Platform-Tools
        self._android_sdk_platform_tools_toolid = self._android_group + ':' + self._android_sdk_platform_tools_artifactid
        self._android_sdk_platform_tools_version = 'r24.0.2'

        # Android SDK Build Tools
        self._android_sdk_build_tools_toolid = self._android_group + ':' + self._android_sdk_build_tools_artifactid
        self._android_sdk_build_tools_version = 'r24.0.2'

        # Android SDK Platform
        self._android_sdk_platform_artifactid = 'platform'
        self._android_sdk_platform_toolid = self._android_group + ':' + self._android_sdk_platform_artifactid
        self._android_sdk_platform_version = '25.3'

        # Android Support Repository
        self._android_support_repository_toolid = self._android_group + ':support-repository'
        self._android_support_repository_version = '47'

        # Google Repository
        self._google_repository_toolid = self._android_group + ':google-repository'
        self._google_repository_version = '51'

    def set_option(self,o,v):
        if o == 'kapsel-version':
            self._kapsel_version = v
            log.info( '\tusing kapsel version ' + v)
        elif o == 'cordova-cli-version':
            self._cordova_cli_version = v
            log.info( '\tusing Cordova CLI version ' + v)
        elif o == 'cordova-build-type':
            if v not in ['debug', 'release']:
                raise XmakeException('Build type {0} is not supported'.format(v))
            self._cordova_build_type = v
            log.info('\tusing {0} Cordova build'.format(v))
        elif o == 'xcode-xcconfig-enterprise':
            self._xcode_xcconfig_enterprise = v
        elif o == 'xcode-xcconfig-naas':
            self._xcode_xcconfig_naas = v
        elif o == 'xcode-xcconfig-local':
            self._xcode_xcconfig_local = v

    def plugin_imports(self):
        return {
            'default': [ ':'.join([self._kapsel_group, 'smp-plugins-dist','zip',self._kapsel_version]) ]
        }

    # list of tools needed to build target project
    def need_tools(self):
        tools = []

        # maven client for Android signing
        def install_maven_client(target_directory, version):
            return os.path.join(target_directory, os.listdir(target_directory)[0])

        tools.append({
            'toolid': self._maven_client_toolid,
            'version': self._maven_client_version,
            'type' : 'zip',
            'classifier' : 'dist',
            'custom_installation' : install_maven_client
        })

        # nodeJS
        def install_nodejs(target_directory, version):
            return os.path.join(target_directory, os.listdir(target_directory)[0])

        tools.append({
            'toolid': self._nodejs_group_artifact,
            'version': self._nodejs_version,
            'type' : 'exe' if self.build_cfg.runtime() == "windows_amd64" else 'tar.gz',
            'classifier' : self._node_classifier,
            'custom_installation' : install_nodejs
        })

         # Tools for Android SDK
        if self._cordova_platform == 'android':
            def firstDirectory(target_directory):
                dirs = os.listdir(target_directory)
                for file in dirs:
                    if file != '.DS_Store':
                        return file

            def install_java(target_directory, version):
                return os.path.join(target_directory, firstDirectory(target_directory))

            def install_gradle(target_directory, version):
                return os.path.join(target_directory, firstDirectory(target_directory))

            def install_android_sdk_tools(target_directory, version):
                return os.path.join(target_directory, 'tools')

            def install_android_sdk_platform_tools(target_directory, version):
                return os.path.join(target_directory, 'platform-tools')

            def install_android_sdk_build_tools(target_directory, version):
                return os.path.join(target_directory, firstDirectory(target_directory))

            def install_android_sdk_platform(target_directory, version):
                return os.path.join(target_directory, firstDirectory(target_directory))

            tools.append({
                'toolid': self._java_toolid,
                'version': self._java_version,
                'type' : 'tar.gz',
                'classifier' : self._java_classifier,
                'custom_installation' : install_java
            })

            tools.append({
                'toolid': self._gradle_toolid,
                'version': self._gradle_version,
                'type' : 'zip',
                'classifier' : 'all',
                'custom_installation' : install_gradle
            })

            tools.append({
                'toolid': self._android_sdk_tools_toolid,
                'version': self._android_sdk_tools_version,
                'type' : 'zip',
                'custom_installation' : install_android_sdk_tools
            })

            tools.append({
                'toolid': self._android_sdk_platform_tools_toolid,
                'version': self._android_sdk_platform_tools_version,
                'type' : 'zip',
                'custom_installation' : install_android_sdk_platform_tools
            })

            tools.append({
                'toolid': self._android_sdk_build_tools_toolid,
                'version': self._android_sdk_build_tools_version,
                'type' : 'zip',
                'custom_installation' : install_android_sdk_build_tools
            })

            tools.append({
                'toolid': self._android_sdk_platform_toolid,
                'version': self._android_sdk_platform_version,
                'type' : 'zip',
                'custom_installation' : install_android_sdk_platform
            })

            tools.append({
                'toolid': self._android_support_repository_toolid,
                'version': self._android_support_repository_version,
                'type' : 'zip',
            })

            tools.append({
                'toolid': self._google_repository_toolid,
                'version': self._google_repository_version,
                'type' : 'zip',
            })

        return tools

    def after_IMPORT(self, build_cfg):
        # Parse information from config.xml
        log.info('Parsing config.xml')
        parsed_xml = minidom.parse(os.path.join(self.build_cfg.src_dir(), 'config.xml'))
        self._config_id = parsed_xml.firstChild.getAttribute('id').encode("utf-8")
        self._config_version = parsed_xml.firstChild.getAttribute('version').encode("utf-8")
        self._config_name = parsed_xml.getElementsByTagName('name')[0].childNodes[0].nodeValue.encode("utf-8")

        log.info('config id: {0}'.format(self._config_id))
        log.info('config version: {0}'.format(self._config_version))
        log.info('config name: {0}'.format(self._config_name))

        # Add the cordova platform as a postfix to the groupid
        self.build_cfg.set_base_group('{0}.{1}'.format(self._config_id, self._cordova_platform))

        # Spaces in artifact id will be converted to '+'
        artifactid = self._config_name.replace(' ', '+')

        # iOS AppStore builds use a different artifact id
        if self._cordova_platform == 'ios' and self._get_ios_build_type() == 'release':
            artifactid = '{0}_release'.format(artifactid)

        self.build_cfg.set_base_artifact(artifactid)

        self.build_cfg.set_base_version(self._config_version)

        if self.build_cfg.version_suffix() is None:
            build_cfg._version = self.build_cfg.base_version()
        else:
            build_cfg.set_version(self.build_cfg.base_version() + "-" + self.build_cfg.version_suffix())

        # Expected build artifacts
        apk_dir = os.path.join(self.build_cfg.gen_dir(), 'platforms' ,'android' ,'build' ,'outputs' ,'apk')
        ipa_dir = ota_path = os.path.join(self.build_cfg.gen_dir(), 'platforms', 'ios', 'build', 'device')

        self._build_artifacts = {
            'android' : {
                'unsigned-apk' : os.path.join(apk_dir, 'android-{0}-unsigned.apk').format(self._cordova_build_type),
                'aligned-apk' : os.path.join(apk_dir, 'android-{0}-aligned.apk').format(self._cordova_build_type),
                'armv7-unsigned-apk' : os.path.join(apk_dir, 'android-armv7-{0}-unsigned.apk').format(self._cordova_build_type),
                'armv7-aligned-apk' : os.path.join(apk_dir, 'android-armv7-{0}-aligned.apk').format(self._cordova_build_type),
                'x86-unsigned-apk' : os.path.join(apk_dir, 'android-x86-{0}-unsigned.apk').format(self._cordova_build_type),
                'x86-aligned-apk' : os.path.join(apk_dir, 'android-x86-{0}-aligned.apk').format(self._cordova_build_type)
            },
            'ios' : {
                'app' : os.path.join(ipa_dir, '{0}.app').format(self._config_name),
                'dSym' : os.path.join(ipa_dir, '{0}.app.dSym').format(self._config_name),
                'ipa' : os.path.join(ipa_dir, '{0}.ipa').format(self._config_name),
                'ota-htm' : os.path.join(ipa_dir, '{0}-ota.htm').format(self._config_name)
            }
        }

        log.info('Extracting Kapsel SDK...')
        kapsel_sdk_zip = os.path.join(self.build_cfg.import_dir(),"smp-plugins-dist-{0}.zip".format(self._kapsel_version))

        if not os.path.exists(self._kapsel_sdk_dir()):
            os.makedirs(self._kapsel_sdk_dir())
            with zipfile.ZipFile(kapsel_sdk_zip, "r") as z:
                z.extractall(self._kapsel_sdk_dir())

    def run(self):
        log.info('Kapsel build started...')

        # Environment setup
        self._setup_node()
        self._setup_cordova()

        if self._cordova_platform == 'android':
            self._setup_android_sdk()

        # Turn off telemetry
        return_code = subprocess.call([
            'cordova', 'telemetry', 'off'
        ])

        if return_code != 0:
            raise XmakeException('Failed to disable Cordova telemetry')

        # Create the Cordova project
        log.info('Running Cordova create...')
        return_code = subprocess.call([
            'cordova', 'create', self.build_cfg.gen_dir(), '--template', self.build_cfg.src_dir()
        ])

        if return_code != 0:
            raise XmakeException('Failed to create Cordova project')

        # For enterprise and company build we need to modify the bundler identifier on iOS
        # .internal postfix for enterprise and .release postfix for company build
        # Note: Technically we should be able to pass the id to the Cordova create command.  However
        # internal (used by enterprise builds) is restricted by Cordova.  Updating the id after
        # create works around this issue for now.
        if self._cordova_platform == 'ios':
            build_type = self._get_ios_build_type()
            if build_type is not None:
                self.update_config_id(self._config_id + '.' + build_type)
                log.info('App id changed to {0}'.format(self._config_id))

        # Add platform to project
        log.info('Running Cordova platform add...')
        return_code = subprocess.call([
            'cordova', 'platform', 'add', self._cordova_platform, '--searchpath', os.path.join(self._kapsel_sdk_dir(), 'plugins')
        ], cwd=self.build_cfg.gen_dir())

        if return_code != 0:
            raise XmakeException('Failed to add platform to Cordova project')

        if self._cordova_platform == 'android':
            self._update_gradle_files(os.path.join(self.build_cfg.gen_dir(), 'platforms', 'android'))
        elif self._cordova_platform == 'ios':
            self._unlock_keychain()

        # Build project
        log.info('Running Cordova build...')

        build_args = [
            'cordova', 'build', self._cordova_platform, '--device', '--{0}'.format(self._cordova_build_type)
        ]

        if self._cordova_platform == 'ios':
            self._set_manual_provisioning_style()

            xcconfig = None
            build_type = self._get_ios_build_type()

            if build_type == 'internal':
                log.info('Enterprise Signing .......')
                xcconfig = self._xcode_xcconfig_enterprise
                build_args.append('--packageType=enterprise')
            elif build_type == 'release':
                log.info('Company Signing .......')
                xcconfig = self._xcode_xcconfig_naas
                build_args.append('--packageType=app-store')
            else:
                log.info('Development Signing .......')
                xcconfig = self._xcode_xcconfig_local
                build_args.append('--packageType=development')

            if xcconfig is not None:
                xcconfig_path = os.path.join(self.build_cfg.component_dir(), xcconfig)
                if os.path.exists(xcconfig_path):
                    with open(xcconfig_path, 'r') as input_file:
                        data = input_file.read()
                        self._add_xcconfig_properties(data)
                else:
                    raise XmakeException('The xcconfig file {0} was not found!'.format(xcconfig_file))

            else:
                log.info('Using generic xcconfig settings')
                self._add_xcconfig_properties({ 'CODE_SIGN_IDENTITY' : 'iPhone Distribution: SAP SE', 'PROVISIONING_PROFILE_SPECIFIER' : '6WQYJS4JUL/SAP_SE_Generic_Distribution_Profile_2017' })

        if self._cordova_browserify:
            build_args.append('--browserify')

        log.info(' '.join(build_args))

        return_code = subprocess.call(build_args, cwd=self.build_cfg.gen_dir())

        if return_code != 0:
            raise XmakeException('Build failed!')

        # Sign build output
        if self._cordova_platform == 'android':
            universal_apk_unsigned = self._build_artifacts['android']['unsigned-apk']
            if os.path.exists(universal_apk_unsigned):
                self._sign_align_apk(universal_apk_unsigned, self._build_artifacts['android']['aligned-apk'])

            armv7_apk_unsigned = self._build_artifacts['android']['armv7-unsigned-apk']
            if os.path.exists(armv7_apk_unsigned):
                self._sign_align_apk(armv7_apk_unsigned, self._build_artifacts['android']['armv7-aligned-apk'])

            x86_apk_unsigned = self._build_artifacts['android']['x86-unsigned-apk']
            if os.path.exists(x86_apk_unsigned):
                self._sign_align_apk(x86_apk_unsigned, self._build_artifacts['android']['x86-aligned-apk'])

        # Generate OTA link for iOS
        if self._cordova_platform == 'ios':
            self.create_ios_ota_html()

    def after_BUILD(self, build_cfg):
        # Generate export file
        ads_path = os.path.join(self.build_cfg.temp_dir(), 'export.ads')
        log.info('\tGenerating ads {0}...'.format(ads_path))

        with open(ads_path, 'w') as f:
            f.write('artifacts builderVersion:"1.1", {\n')
            log.info('\tgroup "{0}", {{\n'.format(self.build_cfg.base_group()))
            f.write('\tgroup "{0}", {{\n'.format(self.build_cfg.base_group()))
            f.write('\t\tartifact "{0}", isVariant:true, {{\n'.format(self.build_cfg.base_artifact()))

            # Android artifacts
            universal_apk = self._build_artifacts['android']['aligned-apk']
            if os.path.exists(universal_apk):
                f.write('\t\t\tfile "{0}", extension: "apk" \n'.format(universal_apk))

            armv7_apk = self._build_artifacts['android']['armv7-aligned-apk']
            if os.path.exists(armv7_apk):
                f.write('\t\t\tfile "{0}", classifier: "armv7", extension: "apk" \n'.format(armv7_apk))

            x86_apk = self._build_artifacts['android']['x86-aligned-apk']
            if os.path.exists(x86_apk):
                f.write('\t\t\tfile "{0}", classifier: "x86", extension: "apk" \n'.format(x86_apk))

            # iOS artifacts
            ios_app = self._build_artifacts['ios']['app']
            if os.path.exists(ios_app):
                zip_file = ios_app + '.zip'
                self._zip_dir(ios_app, zip_file)
                f.write('\t\t\tfile "{0}", classifier: "Release-iphoneos-app", extension: "zip" \n'.format(zip_file))

            dSym = self._build_artifacts['ios']['dSym']
            if os.path.exists(dSym):
                zip_file = dSym + '.zip'
                self._zip_dir(dSym, zip_file)
                f.write('\t\t\tfile "{0}", classifier: "Release-iphoneos-app", extension: "dSYM.zip" \n'.format(zip_file))

            ipa = self._build_artifacts['ios']['ipa']
            if os.path.exists(ipa):
                f.write('\t\t\tfile "{0}", classifier: "Release-iphoneos", extension: "ipa" \n'.format(ipa))

            ota_html = self._build_artifacts['ios']['ota-htm']
            if os.path.exists(ota_html):
                f.write('\t\t\tfile "{0}", classifier: "Release-iphoneos-ota", extension: "htm" \n'.format(ota_html))

            f.write('\t\t}\n')
            f.write('\t}\n')
            f.write('}\n')

        self.build_cfg.set_export_script(ads_path)

    def _kapsel_sdk_dir(self):
        return os.path.join(self.build_cfg.temp_dir(), 'kapsel')

    def update_config_id(self, id):
        config_file = os.path.join(self.build_cfg.gen_dir(), 'config.xml')
        parsed_xml = minidom.parse(config_file)
        parsed_xml.firstChild.setAttribute('id', id)

        config_handle = open(config_file, 'wb')
        parsed_xml.writexml(config_handle)
        config_handle.close()

        self._config_id = id

    def _sign_align_apk(self, src, dest):
        log.info('Signing apk: ' + src)

        args=""
        if os.getenv('SIGNING_CFG_FILE') and os.path.exists(os.getenv('SIGNING_CFG_FILE')):
            log.info('Using remote signing')
            maven_client_cmd =  os.path.join(self.build_cfg.tools()[self._maven_client_toolid][self._maven_client_version], 'bin', 'mavenclient')

            args = [maven_client_cmd]
            args.extend(['--cfg-file',os.getenv('SIGNING_CFG_FILE')])
            args.extend(['--file', src])
            args.extend(['--groupid', self.build_cfg.base_group()])
            args.extend(['--artifactid', self.build_cfg.base_artifact()])
            args.extend(['--version', self.build_cfg.version()])
            args.extend(['--signingtech', 'ANDROID'])
        else:
            log.info('Using local signing')
            args = ['jarsigner']
            args.extend(['-keystore','http://nexus.wdf.sap.corp:8081/nexus/content/groups/build.releases/com/sap/ldi/signing/localSigningKeystore/1.0.0/localSigningKeystore-1.0.0.jks'])
            args.extend(['-storepass','localSigningPassword'])
            args.extend(['-keypass','localSigningPassword'])
            args.extend(['-tsa', 'http://tcs.dmzwdf.sap.corp:1080/invoke/tsa/tsrequest'])
            args.extend([src])
            args.extend(['localSigning'])

        # Launch signing command
        sign_output = subprocess.check_output(args)
        log.info(sign_output)

        # Zip align the apk
        log.info('Align apk file...')
        return_code = subprocess.call([
            'zipalign', '-f', '-v', '4', src, dest
        ])

        if return_code != 0:
            raise XmakeException('Failed to align apk!')

        # Check signing
        log.info('Verify signing...')
        return_code = subprocess.call([
            'jarsigner', '-verify', '-verbose', '-certs', dest
        ])

        if return_code != 0:
            raise XmakeException('apk not signed!')

    def _get_ios_build_type(self):
        if self.build_cfg.build_args() is not None:
            if "-Dbuild-profile=comp" in self.build_cfg.build_args():
                return 'release'
            elif "-Dbuild-profile=ent" in self.build_cfg.build_args():
                return 'internal'
            elif "-Dbuild-profile=dev" in self.build_cfg.build_args():
                return 'internal'
        return None

    def create_ios_ota_html(self):
        log.info('Creating OTA html for iOS')

        ota_template = os.path.join(self._build_plugin_path, 'template', 'ios-ota.htm')
        ota_path = self._build_artifacts['ios']['ota-htm']

        with open(ota_template, 'r') as input_file:
            data = input_file.read()
            data = data.replace("@title@", self.build_cfg.base_artifact())
            data = data.replace("@bundleIdentifier@", self.build_cfg.base_group())
            data = data.replace("@bundleVersion@", self.build_cfg.version())

            with open(ota_path, 'w') as output_file:
                output_file.write(data)

    def _zip_dir(self, src, dest):
        with zipfile.ZipFile(dest, 'w') as zf:
            for root, dirs, files in os.walk(src):
                for file in files:
                    zf.write(os.path.join(root, file))

    def _unlock_keychain(self):
        prodpass_path = self.build_cfg.tools().prodpassaccess()
        prodpass_cmd_out = '`' + prodpass_path +' --credentials-file ' + os.environ['HOME'] + '/.prodpassaccess/credentials.properties --master-file ' + os.environ['HOME'] +'/.prodpassaccess/master.xml get unlock-keychain password`'
        print prodpass_cmd_out
        keychain_file = os.environ['HOME'] + '/Library/Keychains/login.keychain'
        log.info('Unlocking keychain...')
        unlockcommand = 'security unlock-keychain -p ' + prodpass_cmd_out + ' ' + keychain_file
        os.system(unlockcommand)
        unlock_return_code = subprocess.call([
            'security', 'unlock-keychain', '-p', prodpass_cmd_out , keychain_file
        ])

        if unlock_return_code == 0:
            log.info('Keychain unlocked successfully')
        else:
            log.warning('Failed to unlock keychain')

    def _update_gradle_files(self, root):
        log.info('Updating gradle files')
        for root, dirs, files in os.walk(root):
            for file in files:
                if file.endswith(".gradle"):
                    path = os.path.join(root, file)
                    log.info('Found ' + path)
                    for i, line in enumerate(fileinput.input(path, inplace=1)):
                        line = line.replace('mavenCentral()', 'maven { url "http://nexus.wdf.sap.corp:8081/nexus/content/groups/build.releases/" }')
                        line = line.replace('jcenter()', 'maven { url "http://nexus.wdf.sap.corp:8081/nexus/content/groups/build.releases/" }')
                        line = line.replace('https://download.01.org/crosswalk/releases/crosswalk/android/maven2', 'http://nexus.wdf.sap.corp:8081/nexus/content/groups/build.releases')
                        sys.stdout.write(line)

    def _setup_node(self):
        log.info('Setting up node...')
        node_home = self.build_cfg.tools()[self._nodejs_group_artifact][self._nodejs_version]
        global_dir = os.path.join(self.build_cfg.temp_dir(), '.npm-global')

        if not os.path.exists(global_dir):
            os.makedirs(global_dir)

        os.environ["npm_config_userconfig"] = os.path.join(self.build_cfg.temp_dir(), '.npmrc')
        os.environ["npm_config_registry"] = 'http://nexus.wdf.sap.corp:8081/nexus/content/groups/build.releases.npm/'
        os.environ["npm_config_prefix"] = global_dir
        os.environ["PATH"] = os.path.join(node_home, 'bin') + os.pathsep + os.path.join(global_dir, 'lib', 'node_modules') + os.pathsep + os.path.join(global_dir, 'bin') + os.pathsep + os.environ["PATH"]

    def _setup_cordova(self):
        log.info('Setting up Cordova CLI {0}...'.format(self._cordova_cli_version))
        install_cordova_return_code = subprocess.call(['npm','install','-g','cordova@' + self._cordova_cli_version])
        os.environ["CORDOVA_ANDROID_GRADLE_DISTRIBUTION_URL"] = 'http://nexus.wdf.sap.corp:8081/nexus/content/repositories/3rd-party.releases.manual-uploads.hosted/org/gradle/download/gradle/gradle/' + self._gradle_version + '/gradle-' + self._gradle_version + '-all.zip'

        cordova_home = os.path.join(self.build_cfg.temp_dir(), '.cordova')
        if not os.path.exists(cordova_home):
            os.makedirs(cordova_home)

        os.environ["CORDOVA_HOME"] = cordova_home

    def _setup_android_sdk(self):
        # Create java home
        log.info('Setting up Java...')
        java_home = self.build_cfg.tools()[self._java_toolid][self._java_version]
        
        os.environ["JAVA_HOME"] = java_home
        os.environ["PATH"] = os.path.join(java_home, 'bin') + os.pathsep + os.environ["PATH"]
        log.info(java_home)
        # Create gradle home
        log.info('Setting up Gradle...')
        gradle_home = self.build_cfg.tools()[self._gradle_toolid][self._gradle_version]

        os.environ["GRADLE_HOME"] = gradle_home
        os.environ["PATH"] = os.path.join(gradle_home, 'bin') + os.pathsep + os.environ["PATH"]

        log.info('Setting up Android SDK...')
        android_home = os.path.join(self.build_cfg.temp_dir(), 'android_sdk')

        # Create android home
        if not os.path.exists(android_home):
            os.makedirs(android_home)
            os.makedirs(os.path.join(android_home, 'build-tools'))
            os.makedirs(os.path.join(android_home, 'platforms'))
            os.makedirs(os.path.join(android_home, 'extras'))

            tools_path = self.build_cfg.tools()[self._android_sdk_tools_toolid][self._android_sdk_tools_version]
            platform_tools_path = self.build_cfg.tools()[self._android_sdk_platform_tools_toolid][self._android_sdk_platform_tools_version]
            build_tools_path = self.build_cfg.tools()[self._android_sdk_build_tools_toolid][self._android_sdk_build_tools_version]
            platform_path = self.build_cfg.tools()[self._android_sdk_platform_toolid][self._android_sdk_platform_version]
            support_repository_path = self.build_cfg.tools()[self._android_support_repository_toolid][self._android_support_repository_version]
            google_repository_path = self.build_cfg.tools()[self._google_repository_toolid][self._google_repository_version]

            def format_version(v):
                if v.startswith('r'):
                    return v[1:]
                else:
                    return v

            os.symlink(tools_path, os.path.join(android_home, 'tools'))
            os.symlink(platform_tools_path, os.path.join(android_home, 'platform-tools'))
            os.symlink(build_tools_path, os.path.join(android_home, 'build-tools', format_version(self._android_sdk_build_tools_version)))
            os.symlink(platform_path, os.path.join(android_home, 'platforms', 'android-' + self._android_sdk_platform_version))
            os.symlink(support_repository_path, os.path.join(android_home, 'extras', 'android'))
            os.symlink(google_repository_path, os.path.join(android_home, 'extras', 'google'))

        # Update environment variables to point at the android tools.
        os.environ["ANDROID_HOME"] = android_home
        os.environ["PATH"] = os.path.join(android_home, 'tools') + os.pathsep + os.path.join(android_home, 'platform-tools') + os.pathsep + os.path.join(android_home, 'build-tools', format_version(self._android_sdk_build_tools_version)) + os.pathsep + os.environ["PATH"]

        # Gradle
        gradle_user_home = os.path.join(self.build_cfg.temp_dir(), '.gradle')
        if not os.path.exists(gradle_user_home):
            os.makedirs(gradle_user_home)

        os.environ["GRADLE_USER_HOME"] = gradle_user_home

    def _default_cordova_platform(self):
        if sys.platform == "linux" or sys.platform == "linux2":
             # Linux will build Android by default
            return 'android'
        elif sys.platform == "darwin":
            # MACOS will build iOS by default
            return 'ios'
        elif _platform == "win32":
            # Windows will build Android by default
            return 'android'
        else:
            return None;

    def _set_manual_provisioning_style(self):
        pbxproj_path = os.path.join(self.build_cfg.gen_dir(), 'platforms', 'ios', self._config_name + '.xcodeproj', 'project.pbxproj')

        if os.path.exists(pbxproj_path):
            with open (pbxproj_path, 'r+') as pbxproj:
                data=pbxproj.read()
                target = re.search('targets = \(\n\s+(\w+)\s', data, re.M)

                if target:
                    search_string = 'attributes = {\n'
                    data = data.replace(search_string, search_string + '\t\t\t\tTargetAttributes = {\n\t\t\t\t\t' + target.group(1) + ' = {\n\t\t\t\t\t\tProvisioningStyle = Manual;\n\t\t\t\t\t};\n\t\t\t\t};\n')
                    pbxproj.seek(0)
                    pbxproj.write(data)
                    pbxproj.truncate()

    def _add_xcconfig_properties(self, properties):
        xcconfig_path = os.path.join(self.build_cfg.gen_dir(), 'platforms', 'ios', 'cordova', 'build.xcconfig')

        if os.path.exists(xcconfig_path):
            with open (os.path.join(dir, xcconfig_path), 'a') as xcconfig:
                if isinstance(properties, dict):
                    for key in properties:
                        xcconfig.write('\n' + key + ' = ' + properties[key])
                else:
                    xcconfig.write(properties)

    def _get_development_team(self):
        teams = self._get_development_teams()
        if len(teams) == 1:
            teamId = teams[0]['id']
            log.info('Found and using the following development team installed on your system: ' + teams[0]["name"] + ' (' + teams[0]["id"] + ')')
        elif len(teams) > 0:
            log.warning('Multiple development teams installed on your system. Will use the first matching team: ' + teams[0]["name"] + ' (' + teams[0]["id"] + ')')
            teamId = teams[0]['id']

        return teamId;

    def _get_development_teams(self):
        teamIds = {};
        dir = os.path.join(os.path.expanduser('~'), 'Library/MobileDevice/Provisioning Profiles/');
        files = os.listdir(dir)

        for file in files:
            if file.endswith('.mobileprovision'):
                data = ''
                with open (os.path.join(dir, file), 'r') as openedfile:
                    data=openedfile.read()

                teamId = self._get_provisioning_profile_value('TeamIdentifier', data);
                teamName = self._get_provisioning_profile_value('TeamName', data);

                if teamId:
                    teamIds[teamId] = teamName


        teamIdsArray = []
        for teamId in teamIds:
            teamIdsArray.append({'id':teamId, 'name':teamIds[teamId]})

        return teamIdsArray;


    def _get_provisioning_profile_value(self, name, text):
        findStr = '<key>' + name + '</key>'
        index = text.find(findStr)
        if index > 0:
            index = text.find('<string>', index + len(findStr))
            if index > 0:
                index += len('<string>')
                endIndex = text.find('</string>', index)
                result = text[index: endIndex]
                return result
        return null;
