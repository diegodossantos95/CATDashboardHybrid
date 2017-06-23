'''
Created on 12.12.2016

@author: I041864
'''



import logging
import log
import os
import xmake_exceptions
import shutil
import tempfile
import re
import spi

logger = logging.getLogger('buildplugin')



class buildline:
    '''
        Prepare separate build line with arguments for each solution and/or project file.
    '''

    solution = ""
    vcvarsall = ""
    pltf = ""
    detailedsummary = ""
    target = ""
    verbosity = ""
    nodeReuse = ""
    maxcpucount = ""
    property = ""

    def solution_file_check(self, solution_file):
        '''
            Check if a solution or a project file exist.
        '''

        solution_file = os.path.join(self.build_cfg.temp_dir(), 'src', solution_file)

        if not os.path.isfile(solution_file):
            raise xmake_exceptions.XmakeException("ERR: The defined solution or project file does not exist \"%s\" " % solution_file)

        return solution_file

    def msvs_check(self, msvs):
        '''
            Checking if the required or the default MSVS version is installed on the server.
        '''

        logging.info("Checking if the required MSVS version is installed on the server.")

        if msvs == "":
            logging.info("MSVS version is not defined, so the default 2015 will be used.")
            vcvarsall = os.path.join(self.build_cfg.xmake_msvc140_dir, 'VC', 'vcvarsall.bat')
        elif msvs == "2015":
            vcvarsall = os.path.join(self.build_cfg.xmake_msvc140_dir, 'VC', 'vcvarsall.bat')
        elif msvs == "2013":
            vcvarsall = os.path.join(self.build_cfg.xmake_msvc120_dir, 'VC', 'vcvarsall.bat')
        elif msvs == "2012":
            vcvarsall = os.path.join(self.build_cfg.xmake_msvc110_dir, 'VC', 'vcvarsall.bat')
        elif msvs == "2010":
            vcvarsall = os.path.join(self.build_cfg.xmake_msvc100_dir, 'VC', 'vcvarsall.bat')
        else:
            logging.warning("The defined MSVS version %s is not supported, so the default 2015 will be used instead." % msvs)
            vcvarsall = os.path.join(self.build_cfg.xmake_msvc140_dir, 'VC', 'vcvarsall.bat')

        if not os.path.isfile(vcvarsall):
            raise xmake_exceptions.XmakeException("ERR: The defined vcvarsall \"%s\" file does not exist, i.e. the required MSVS version is not installed on this build server." % vcvarsall)

        return vcvarsall

    def pltf_check(self, pltf):
        '''
            Checking the platform version.
        '''

        if pltf == "":
            logging.info("Platform version is not defined, so the default x86 will be used.")
            pltf = "x86"
        elif not (pltf == "x86" or pltf == "x86_amd64" or pltf == "amd64_x86" or pltf == "amd64" or pltf == "x86_ia64" or pltf == "ia64" or pltf == "arm" or pltf == "x86_arm" or pltf == "amd64_arm"):
            logging.warning("The defined platform version %s is not supported, so the default x86 will be used instead." % pltf)
            pltf = "x86"

        return pltf

    def target_check(self, target):
        '''
            Checking the target(s) predefined.
        '''

        if target == "":
            log.info("Target is not defined, so the default will be used.")
            target = ""
        else:
            target = "/target:" + target

        return target

    def verbosity_check(self, verbosity):
        '''
            Checking the verbosity level of the compilation output.
        '''

        if verbosity == "":
            logging.info("Verbosity level is not defined, so the default will be used.")
            verbosity = ""
        elif not (verbosity == "q" or verbosity == "quiet" or verbosity == "m" or verbosity == "minimal" or verbosity == "n" or verbosity == "normal" or verbosity == "d" or verbosity == "detailed" or verbosity == "diag" or verbosity == "diagnostic"):
            logging.warning("The defined verbosity level %s is not supported, so the default will be used instead." % verbosity)
            verbosity = ""
        else:
            verbosity = "/verbosity:" + verbosity

        return verbosity

    def nodeReuse_check(self, nodeReuse):
        '''
            Checking the nodeReuse argument.
        '''

        if nodeReuse == "":
            logging.info("nodeReuse state is not defined, so the default will be used.")
            nodeReuse = ""
        elif not (nodeReuse == "True" or nodeReuse == "False"):
            logging.warning("The defined nodeReuse state %s is not supported, so the default will be used instead." % nodeReuse)
            nodeReuse = ""
        else:
            nodeReuse = "/nodeReuse:" + nodeReuse

        return nodeReuse

    def maxcpucount_check(self, maxcpucount):
        '''
            Checking maxcpucount argument.
        '''

        if maxcpucount == "":
            logging.warning("maxcpucount value is not defined, but using all of the server CPUs is not allowed, so the default value 1 will be used instead.")
            maxcpucount = ""
        elif not (maxcpucount == "1" or maxcpucount == "2" or maxcpucount == "3" or maxcpucount == "4" or maxcpucount == "5" or maxcpucount == "6"):
            logging.warning("The defined maxcpucount value %s is not supported or allowed, so the default value 1 will be used instead." % maxcpucount)
            maxcpucount = ""
        else:
            maxcpucount = "/maxcpucount:" + maxcpucount

        return maxcpucount

    def property_check(self, property):
        '''
            Checking the property(ies) predefined.
        '''

        if property == "":
            log.info("Property is not defined, so the default will be used.")
            property = ""
        else:
            property = "/property:" + property

        return property

    def __init__(self, buildarguments, build_cfg):
        '''
            Initializing a build line arguments for a solution or a project file.
        '''

        self.build_cfg = build_cfg;
        self._options = {}

        build_out_dir = os.path.join(self.build_cfg.component_dir(), 'gen', 'out')

        for buildargument in buildarguments:
            if "solution=" in buildargument:
                self.solution = self.solution_file_check(buildargument.strip().split('=')[-1])
            elif "msvs=" in buildargument:
                self.vcvarsall = self.msvs_check(buildargument.strip().split('=')[-1])
            elif "pltf=" in buildargument:
                self.pltf = self.pltf_check(buildargument.strip().split('=')[-1])
            elif "detailedsummary" in buildargument:
                self.detailedsummary = "/detailedsummary"
            elif "target:" in buildargument:
                self.target = self.target_check(buildargument.strip().split(':')[-1])
            elif "verbosity:" in buildargument:
                self.verbosity = self.verbosity_check(buildargument.strip().split(':')[-1])
            elif "nodeReuse:" in buildargument:
                self.nodeReuse = self.nodeReuse_check(buildargument.strip().split(':')[-1])
            elif "maxcpucount:" in buildargument:
                self.maxcpucount = self.maxcpucount_check(buildargument.strip().split(':')[-1])
            elif "property:" in buildargument:
                self.property = self.property_check(buildargument.strip().split(':')[-1])
            else:
                logging.warning("Not supported build argument %s could not be included into the build options." % buildargument)

        if self.solution == "":
            raise xmake_exceptions.XmakeException("ERR: At least one dotnet solution or project file to be compiled should be defined.")

        if self.vcvarsall == "":
            self.vcvarsall = self.msvs_check("")

        if self.pltf == "":
            self.pltf = self.pltf_check("")



class BuildPlugin(spi.BuildPlugin):
    '''
        Xmake dotnet build plugin class that provides the ability to compile dotnet project with one or many solution and/or project files.
    '''

    def __init__(self, build_cfg):
        self.build_cfg = build_cfg;
        self._options = {}

    def run(self):
        '''
            Build source files
        '''

        logging.info("Invoking dotnet build plug-in.")

        if os.name == 'posix':
            raise xmake_exceptions.XmakeException("ERR: The dotnet build plug-in is supported to run only on Windows.")

        self._clean_if_requested()

        self._copied_src_dir = os.path.join(self.build_cfg.temp_dir(), 'src')
        self._copy_src_dir_to(self._copied_src_dir)

        dotnetconfig = os.path.join(self.build_cfg.component_dir(), 'cfg', 'dotnet.cfg')
        if not os.path.isfile(dotnetconfig):
            raise xmake_exceptions.XmakeException("ERR: The mandatory cfg\\dotnet.cfg file is missing.")
        buildconfigfile = open(dotnetconfig, 'rb')
        buildconfig = [row.strip().split(' ') for row in buildconfigfile]
        builds = [buildline(buildconfig[i],self.build_cfg) for i in range(len(buildconfig))]

        with open("dotnet-build.bat", "w") as f:
            f.write("@echo off" + "\n")
            f.write("setlocal" + "\n")
            f.write("@echo INFO: Start building on server %computername% with user %username% in workspace %cd% on date %date% at time %time%" + "\n")
            for build in builds:
                f.write("@echo INFO: call \"" + build.vcvarsall + "\" " + build.pltf + "\n")
                f.write("call \"" + build.vcvarsall + "\" " + build.pltf + "\n")
                f.write("@echo INFO: msbuild" + " " + build.nodeReuse + " " + build.maxcpucount + " " + build.detailedsummary + " " + build.verbosity + " " + build.property + " " + build.solution + " " + build.target + "\n")
                f.write("msbuild" + " " + build.nodeReuse + " " + build.maxcpucount + " " + build.detailedsummary + " " + build.verbosity + " " + build.property + " " + build.solution + " " + build.target + "\n")
                f.write("if %errorlevel% neq 0 exit /b %errorlevel%" + "\n")
                f.write("@echo INFO: The build of solution / project " + build.solution + " has completed successfully." + "\n")
            f.write("endlocal" + "\n")
            f.write("exit 0" + "\n")

        rc = log.log_execute(["dotnet-build.bat"])
        if rc > 0:
            raise xmake_exceptions.XmakeException("ERR: .NET build plug-in returned %s" % str(rc))

        return 0

    def _copy_src_dir_to(self, todir):
        '''
            Copy source files in another directory to avoid modifications in original source files.
        '''

        if os.path.exists(todir):
            logging.info('removing existing folder', todir)
            targetDirectory = os.path.join(todir, 'target')
            if os.path.exists(targetDirectory):
                logging.debug('target directory was generated, so we keep it as it is in directory {}'.format(targetDirectory))
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

        logging.info('copying files from', self.build_cfg.component_dir(), 'to', todir)

        for directory in os.listdir(self.build_cfg.component_dir()):
            if directory not in ['.xmake', '.xmake.cfg', 'gen', 'import', 'imports', 'cfg', '.git', '.gitignore', 'target']:
                pathToCopy = os.path.join(self.build_cfg.component_dir(), directory)
                if os.path.isdir(pathToCopy):
                    shutil.copytree(pathToCopy, os.path.join(todir, directory))
                else:
                    shutil.copyfile(pathToCopy, os.path.join(todir, directory))
