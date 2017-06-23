'''

@author: i302336
'''
import ExternalTools
import xmake_exceptions
import log
import os
import re
import tarfile
import shutil
import sys
import spi
from ExternalTools import OS_Utils

class BuildPlugin(spi.BuildPlugin):
    def __init__(self, build_cfg):
        self.build_cfg = build_cfg
        self._copied_src_dir = os.path.join(self.build_cfg.temp_dir())
        self._dst_dir = os.path.join(self.build_cfg.component_dir(), 'gen', 'out')
        self.sid=''
        self.type=''
        self.BAS2_DEPOT_DIR=''
        self.PEDANTIC_DEPENDENCIES=''
        self.SAP_PLATFORM=''
        self.ccq=''
        self.CCQ_IGNORE=''
        self.sapmake_log=''
        self.trace=''
        self.sapmake_lib=''
        self.sapmake_j=''
        self.sapmake_l=''
        self.sapmake_k=''
        self.project=''
        self.target=''
        
        self.msvs=''
        self.pltf=''
        self.vcvarsall=''
        
        self.get_parameters()
        self._copy_src_dir_to(self._copied_src_dir)
        self._copied_src_dir = os.path.join(self.build_cfg.temp_dir(), 'src')
        
        self._options = {}


    def run(self):
        log.info("******************************")
        log.info("invoking sapmake....")
        log.info("******************************")
        
        
        #sapmake_home = os.path.join(self.build_cfg.tools()["sapmake"][self._options["sapmake"]], "src")
        sapmake_pl_home  = os.path.join(self.build_cfg.src_dir(), "./sapmake", "sapmk.pl")
        #print ("Sapmake_pl_home: %s", sapmake_pl_home)
        #print (self.build_cfg.component_dir())
        #print (self.build_cfg.src_dir())
        #print (self._copied_src_dir)

        #log.info(sapmake_home)
        if os.name == 'posix':
            
            os.chdir(self.build_cfg.component_dir())
            script_name = os.path.join(self.build_cfg.component_dir(), "run.sh")
            
            with open(script_name, "wb+") as f:
                f.write(self.construct_build_line())

            rc = log.log_execute(["sh", script_name])
            if rc > 0: 
                raise xmake_exceptions.XmakeException("ERR: sapmake returned %s" % str(rc))
        else:
            #print (self.construct_build_line())
            self.msvs_check()
            self.pltf_check()
            
            os.chdir(self.build_cfg.component_dir())
            script_name = os.path.join(self.build_cfg.component_dir(), "run.bat")
            
            sapmake_loc = os.path.join(self.build_cfg.component_dir(), 'src', 'sapmake')
            
            
            with open(script_name, "wb+") as f:
                f.write("set path=%path%;" + sapmake_loc + "\n")
                f.write("call \"" + self.vcvarsall + "\" " + self.pltf + "\n")
                f.write(self.construct_build_line())
                
            rc = log.log_execute([script_name])
            
            if rc > 0: 
                raise xmake_exceptions.XmakeException("ERR: sapmake returned %s" % str(rc))

        return 0
    
    def _copy_src_dir_to(self, todir):
        '''
            Copy source files in another directory to avoid modifications in original source files.
        '''

        if os.path.exists(todir):
            log.info('removing existing folder', todir)
            targetDirectory = os.path.join(todir, 'target')
            if os.path.exists(targetDirectory):
                log.debug('target directory was generated, so we keep it as it is in directory {}'.format(targetDirectory))
                tmpDir = os.path.join(tempfile.mkdtemp(), 'target')
                shutil.copytree(targetDirectory, tmpDir)
                OS_Utils.rm_dir(todir)
                os.mkdir(todir)
                shutil.copytree(tmpDir, targetDirectory)
                shutil.rmtree(tmpDir)
            else:
                OS_Utils.rm_dir(todir)
                os.mkdir(todir)
        else:
            os.mkdir(todir)

        log.info('copying files from', self.build_cfg.component_dir(), 'to', todir)

        for directory in os.listdir(self.build_cfg.component_dir()):
            if directory not in ['.xmake.cfg', 'gen', 'import', 'cfg', '.git', '.gitignore', 'target']:
                pathToCopy = os.path.join(self.build_cfg.component_dir(), directory)
                if os.path.isdir(pathToCopy):
                    shutil.copytree(pathToCopy, os.path.join(todir, directory))
                else:
                    shutil.copyfile(pathToCopy, os.path.join(todir, directory))

    def construct_build_line(self):
        """
            Constructs a build command for the platform of the build
        """
        build_command=''
        build_command+='perl -S ' + os.path.join(self._copied_src_dir, 'sapmake', 'sapmk.pl')
        if not self.sid=='':
            build_command+=' -sid ' + self.sid
        if not self.type=='':
            build_command+=' -type ' + self.type
        if not self.BAS2_DEPOT_DIR=='':
            build_command+=' -BAS2_DEPOT_DIR=' + self.BAS2_DEPOT_DIR
        build_command+=' -src ' + self._copied_src_dir
        build_command+=' -dst ' + self._dst_dir
        if not self.PEDANTIC_DEPENDENCIES=='':
            build_command+=' PEDANTIC_DEPENDENCIES=' + self.PEDANTIC_DEPENDENCIES
        if not self.SAP_PLATFORM=='':
            build_command+=' SAP_PLATFORM=' + self.SAP_PLATFORM
        if not self.ccq=='':
            build_command+=' -ccq ' + self.ccq
        if not self.CCQ_IGNORE=='':
            build_command+=' CCQ_IGNORE=' + self.CCQ_IGNORE
        if not self.sapmake_log=='':
            build_command+=' -log'
        if not self.trace=='':
            build_command+=' -trace ' + self.trace
        if not self.sapmake_lib=='':
            build_command+=' -lib ' + self.sapmake_lib
        if not self.sapmake_j=='':
            build_command+=' -j ' + self.sapmake_j
        if not self.sapmake_l=='':
            build_command+=' -l ' + self.sapmake_l
        if not self.sapmake_k=='':
            build_command+=' -k'
        if not self.project=='':
            build_command+=' -p ' + self.project
        if not self.target=='':
            build_command+=' ' + self.target
        
        build_command+=' -scratch'
        return build_command
        #-sid CGK -src /data/xmake/SlaveProd/workspace/sapmake_plugin_xmake_sample-xmake_test-CI-P4-linuxx86_64-linuxx86_64/src -dst /data/xmake/SlaveProd/workspace/sapmake_plugin_xmake_sample-xmake_test-CI-P4-linuxx86_64-linuxx86_64/gen/out -ccq off -p regex all -scratch
        
    def get_parameters(self):
        """
            Reads the parameters from sapmake.cfg file
        """
        configfile = os.path.join(self.build_cfg.component_dir(), 'cfg', 'sapmake.cfg')
        configuration = open(configfile, 'rb')
        configfileline = [row.strip().split(' ') for row in configuration]
        buildconfig = configfileline[0]
        
        #Add more parameters for the build
        for i in range(len(buildconfig)):
            if "sid=" in buildconfig[i]:
                self.sid = buildconfig[i].strip().split('=')[-1]
            elif "type=" in buildconfig[i]:
                self.type = buildconfig[i].strip().split('=')[-1]
            elif "BAS2_DEPOT_DIR=" in buildconfig[i]:
                self.BAS2_DEPOT_DIR = buildconfig[i].strip().split('=')[-1]
            elif "PEDANTIC_DEPENDENCIES=" in buildconfig[i]:
                self.PEDANTIC_DEPENDENCIES = buildconfig[i].strip().split('=')[-1]
            elif "SAP_PLATFORM=" in buildconfig[i]:
                self.SAP_PLATFORM = buildconfig[i].strip().split('=')[-1]
            elif "ccq=" in buildconfig[i]:
                self.ccq = buildconfig[i].strip().split('=')[-1]
            elif "CCQ_IGNORE=" in buildconfig[i]:
                self.CCQ_IGNORE = buildconfig[i].strip().split('=')[-1]
            elif "sapmake_log=" in buildconfig[i]:
                self.sapmake_log = buildconfig[i].strip().split('=')[-1]
            elif "trace=" in buildconfig[i]:
                self.trace = buildconfig[i].strip().split('=')[-1]
            elif "sapmake_lib=" in buildconfig[i]:
                self.sapmake_lib = buildconfig[i].strip().split('=')[-1]
            elif "sapmake_j=" in buildconfig[i]:
                self.sapmake_j = buildconfig[i].strip().split('=')[-1]
            elif "sapmake_l=" in buildconfig[i]:
                self.sapmake_l = buildconfig[i].strip().split('=')[-1]
            elif "sapmake_k=" in buildconfig[i]:
                self.sapmake_k = buildconfig[i].strip().split('=')[-1]
            elif "project=" in buildconfig[i]:
                self.project = buildconfig[i].strip().split('=')[-1]
            elif "target=" in buildconfig[i]:
                self.target = buildconfig[i].strip().split('=')[-1]
            #Those parameters are only relevant for Windows build
            elif "msvs=" in buildconfig[i]:
                self.msvs = buildconfig[i].strip().split('=')[-1]
            elif "pltf=" in buildconfig[i]:
                self.pltf = buildconfig[i].strip().split('=')[-1]
            else: 
                log.error("Not supported argument")

        return 0
        
    def msvs_check(self):
        '''
            Checking if the required or the default MSVS version is installed on the server.
        '''

        log.info("Checking if the required MSVS version is installed on the server.")

        if self.msvs == "":
            log.info("MSVS version is not defined, so the default 2015 will be used.")
            self.vcvarsall = os.path.join(self.build_cfg.xmake_msvc140_dir, 'VC', 'vcvarsall.bat')
        elif self.msvs == "2015":
            self.vcvarsall = os.path.join(self.build_cfg.xmake_msvc140_dir, 'VC', 'vcvarsall.bat')
        elif self.msvs == "2013":
            self.vcvarsall = os.path.join(self.build_cfg.xmake_msvc120_dir, 'VC', 'vcvarsall.bat')
        elif self.msvs == "2012":
            self.vcvarsall = os.path.join(self.build_cfg.xmake_msvc110_dir, 'VC', 'vcvarsall.bat')
        elif self.msvs == "2010":
            self.vcvarsall = os.path.join(self.build_cfg.xmake_msvc100_dir, 'VC', 'vcvarsall.bat')
        else:
            log.warning("The defined MSVS version %s is not supported, so the default 2015 will be used instead." % msvs)
            self.vcvarsall = os.path.join(self.build_cfg.xmake_msvc140_dir, 'VC', 'vcvarsall.bat')

        if not os.path.isfile(vcvarsall):
            raise xmake_exceptions.XmakeException("ERR: The defined vcvarsall \"%s\" file does not exist, i.e. the required MSVS version is not installed on this build server." % vcvarsall)

        return 0

    def pltf_check(self):
        '''
            Checking the platform version.
        '''

        if self.pltf == "":
            log.info("Platform version is not defined, so the default x86 will be used.")
            self.pltf = "x86"
        elif not (pltf == "x86" or pltf == "x86_amd64" or pltf == "amd64_x86" or pltf == "amd64" or pltf == "x86_ia64" or pltf == "ia64" or pltf == "arm" or pltf == "x86_arm" or pltf == "amd64_arm"):
            log.warning("The defined platform version %s is not supported, so the default x86 will be used instead." % pltf)
            self.pltf = "x86"

        return 0
    