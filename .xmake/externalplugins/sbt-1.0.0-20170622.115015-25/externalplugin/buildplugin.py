import fnmatch
import os
import re
import shutil
import subprocess
import tempfile
import zipfile
import log
import spi
from xmake_exceptions import XmakeException

class BuildPlugin(spi.JavaBuildPlugin):

    def __init__(self, build_cfg):
        spi.JavaBuildPlugin.__init__(self, build_cfg)

        self._copied_src_dir = os.path.join(self.build_cfg.temp_dir(), 'src')
        self._sbt_group_artifact = 'com.typesafe.sbt:sbt-launcher'
        self._sbt_version = '0.13.6'
        self._sbt_tasks = ['test', 'package']
        self._sbt_options = []
        self._add_sbt_version_to_artifact = False
        self._add_scala_version_to_artifact = False
        self._java_options = []
        self._ignore_artifact_wildcards = []

        self._repositories_file = os.path.join(self.build_cfg.genroot_dir(), 'repositories')
        self._ads_path = os.path.join(self.build_cfg.temp_dir(), 'export.ads')
        self.build_cfg.set_export_script(self._ads_path)

    def set_option(self,o,v):
        if o == 'sbt-group-artifact':
            self._sbt_group_artifact = v
            log.info( '\tusing sbt ' + v)

        elif o == 'sbt-version':
            self._sbt_version = v
            log.info( '\tusing sbt version ' + v)

        elif o == 'sbt-tasks':
            self._sbt_tasks = v.split(",")
            log.info( '\tusing sbt tasks ' + v)

        elif o == 'sbt-options':
            self._sbt_options.extend(v.split(" "))
            log.info( '\tusing sbt options ' + v)

        elif o == 'add-sbt-version-to-artifact':
            self._add_sbt_version_to_artifact = v.strip().lower() == 'true'
            log.info( '\tadd sbt version to artifact ' + v)

        elif o == 'add-scala-version-to-artifact':
            self._add_scala_version_to_artifact = v.strip().lower() == 'true'
            log.info( '\tadd scala version to artifact ' + v)

        elif o == 'ignore-artifact-wildcards':
            self._ignore_artifact_wildcards = v.split(" ")
            log.info( '\tusing ignore artifact wildcards ' + v)

        elif o == 'java-options':
            self._java_options = v.split(" ")
            log.info( '\tusing java options ' + v)

        else:
            log.error("Unknown option " + o)

    def plugin_imports(self):
        result = {'default': ['{}:jar:{}'.format(self._sbt_group_artifact, self._sbt_version)]}
        return result

    # main
    def java_run(self):
        log.info('Build in progress...')

        self._sbt_run_tasks(self._sbt_tasks)

        log.info('Build done!')

    def _sbt_run_tasks(self, tasks, handler=None):
        jar_path = os.path.join(
            self.build_cfg.import_dir(),
            '{}-{}.jar'.format(self._sbt_group_artifact.split(':')[1], self._sbt_version))
        if not os.path.exists(jar_path):
            raise XmakeException("Could not find sbt launcher " + jar_path)

        base_cmd = ['-jar', jar_path]
        java_options = []
        if self._java_options != None:
            java_options.extend(self._java_options)
        repository_config = ['-Dsbt.override.build.repos=true', '-Dsbt.repository.config=' + self._repositories_file]
        nonProxyHosts = 'localhost|127.0.0.1|*.wdf.sap.corp|*.mo.sap.corp|*.sap.corp'
        proxy_config = ['-Dhttp.nonProxyHosts=' + nonProxyHosts, '-Dhttps.nonProxyHosts=' + nonProxyHosts]
        extra_config= ['-Dsbt.log.noformat=true']
        java_options.extend(repository_config + proxy_config + extra_config)
        full_cmd = java_options + base_cmd + self._sbt_options + tasks
        log.info('sbt command path {}'.format(full_cmd))

        cwd = os.getcwd()
        try:
            os.chdir(self._copied_src_dir)
            rc = self.java_log_execute(full_cmd, handler=handler)
            if rc > 0:
                raise XmakeException('sbt returned %s' % str(rc))
        finally:
            os.chdir(cwd)


    # override any of these to get notifications of phase completions
    def after_PRELUDE(self, build_cfg): pass
    def after_MODULES(self, build_cfg): pass

    def after_IMPORT(self, build_cfg):

        self.java_set_environment(True)

        self._copy_src_dir_to(self._copied_src_dir)

        # Generate content of the repositories file
        content = "\n".join([
            "[repositories]",
            "  local"
        ]) + "\n"

        count = 0
        for import_repo in self.build_cfg.import_repos():
            count += 1
            content += "  standard-" + str(count) + ": " + import_repo + "\n"
            content += "  standard-a-" + str(count) + ": " + import_repo + ", [organisation]/[module]/[revision]/[type]s/[artifact].[ext]\n"
            content += "  standard-b-" + str(count) + ": " + import_repo + ", [organisation]/[module]/[revision]/[type]s/[artifact](-[classifier]).[ext]\n"
            content += "  standard-c-" + str(count) + ": " + import_repo + ", [organisation]/[module]/(scala_[scalaVersion]/)(sbt_[sbtVersion]/)[revision]/[type]s/[artifact].[ext]\n"

        with open(self._repositories_file, "w") as fh:
            fh.write(content)

        # If set-version option is on
        if build_cfg.get_next_version() is not None:
            log.error("Can't set version")

        elif build_cfg.base_version() == 'NONE':
            self._get_version_from_sbt()

        self.actual_sbt_version = self._get_sbt_version_from_sbt()
        self.actual_scala_version = self._get_scala_version_from_sbt()

    def after_BUILD(self, build_cfg):
        # Generate ads file before the export phase
        if not os.path.exists(build_cfg.export_script()):
            log.info('building artifact deployer script (ads file)')
            self._generate_ads_file()
            log.info('artifact deployer script generated')

    def after_EXPORT(self, build_cfg): pass
    def after_DEPLOY(self, build_cfg): pass
    def after_PROMOTE(self, build_cfg): pass
    def after_FORWARD(self, build_cfg): pass

    def _get_scala_version_from_sbt(self):
        version = self._get_last_line_of_output_fom_sbt('scalaVersion')
        version = self._get_major_minor_version(version)
        log.info("Retrieved Scala version from SBT: (" + version + ")")
        return version

    def _get_sbt_version_from_sbt(self):
        version = self._get_last_line_of_output_fom_sbt('sbtVersion')
        version = self._get_major_minor_version(version)
        log.info("Retrieved SBT version from SBT: (" + version + ")")
        return version

    def _get_version_from_sbt(self):
        version = self._get_last_line_of_output_fom_sbt('version')
        log.info("Retrieved version from SBT: (" + version + ")")
        self.build_cfg.set_base_version(version)
        if self.build_cfg.version_suffix():
            self.build_cfg.set_version('{}-{}'.format(version, self.build_cfg.version_suffix()))
        else:
            self.build_cfg.set_version(version)

    def _get_last_line_of_output_fom_sbt(self, task):
        output = []
        def handler(line):
            output.append(line)

        self._sbt_run_tasks([task], handler=handler)
        lastLine = output[-1]
        lastLine = lastLine.strip()
        regex = re.compile(r"^(INFO:|\[info\])\s*([^ ]*)\s*$")
        result = regex.match(lastLine).group(2).strip()
        return result

    def _get_major_minor_version(self, version):
        '''Given a version like 0.13.13 or 2.10.6, returns only the major.minor
           part of that version number, i.e. 0.13 and 2.10, respectively'''
        regex = re.compile(r"^([0-9]+\.[0-9]+)")
        majorMinor = regex.match(version).group(1)
        return majorMinor

    def _generate_ads_file(self):
        '''
            Create the artifact deployer script file
        '''
        # Retrieve artifacts from local deployment repo
        artifacts = self._find_artifacts()

        content = []
        content.append('artifacts builderVersion:"1.1", {')
        for key in artifacts:
            values = artifacts[key]
            gav = key.split(':')
            group = gav[0]
            aid= gav[1]
            if (self._add_scala_version_to_artifact):
                aid = aid + '_' + self.actual_scala_version
            if (self._add_sbt_version_to_artifact):
                aid = aid + '_' + self.actual_sbt_version
            content.append('\tgroup "%s", {' %group)
            content.append('\t\tartifact "%s", {' %aid)

            for (gid, aid, version, classifier, extension, fullPath) in values:
                log.info("artifact to deploy "+ fullPath)
                fileLine = '\t\t\t file "%s"' % fullPath.replace('\\', '/')
                if not classifier == "":
                    fileLine = fileLine + ', classifier:"%s"' % (classifier)
                if not extension == "":
                    fileLine = fileLine + ', extension:"%s"' % (extension)
                content.append(fileLine)
            content.append('\t\t}')
            content.append('\t}')
        content.append('}\n')

        content_string = '\n'.join(content)

        with open(self._ads_path, 'w') as f:
            f.write(content_string)

    def _find_artifacts(self):
        result = dict()
        scala_regex = re.compile('scala-[0-9]+(\\.[0-9]+(\\.[0-9]+)?)?')
        base_dir = self.build_cfg.component_dir()
        if self.build_cfg.alternate_path() != None:
            base_dir = self.build_cfg.alternate_path()
        for dirname, _a, filenames in os.walk(base_dir):
            if 'target' in dirname and scala_regex.search(dirname):
                for filename in filenames:
                    if filename.endswith(".jar"):
                        if self._is_artifact_to_ignore(filename):
                            log.info("Ignoring " + os.path.join(dirname, filename) +
                              " due to ignore-artifact-wildcard settings")
                            continue
                        fullPath = os.path.join(dirname, filename)
                        zip = zipfile.ZipFile(fullPath)
                        manifest = zip.open("META-INF/MANIFEST.MF", "rU")
                        gid = ""
                        aid = ""
                        version = ""
                        for line in manifest.readlines():
                            parts = map(lambda s: s.strip(), line.split(":"))
                            if len(parts) != 2: continue
                            if parts[0] == 'Implementation-Vendor':
                                gid = parts[1]
                            elif parts[0] == 'Implementation-Title':
                                aid = parts[1]
                            elif parts[0] == 'Implementation-Version':
                                version = parts[1]
                        classifier = ""
                        extension = "jar"
                        key = "%s:%s:%s" % (gid, aid, version)
                        artifact = (gid, aid, version, classifier, extension, fullPath)
                        if key not in result:
                            result[key] = list()
                        result[key].append(artifact)
        return result


    def _is_artifact_to_ignore(self, filename):
        ''' Checks if the given artifact filename should be ignored as an artifact.
            This is helpful when unneeded root_*.jar files are generated in a root project.
        '''
        result = False
        for pattern in self._ignore_artifact_wildcards:
            if fnmatch.fnmatch(filename, pattern):
                result = True
                break
        return result

    def _copy_src_dir_to(self, todir):
        '''
            Copy source files in another directory to avoid modifications in original source files.
        '''

        if os.path.exists(todir):
            log.info('removing existing folder', todir)
            shutil.rmtree(todir)

        os.mkdir(todir)

        log.info('copying files from', self.build_cfg.component_dir(), 'to', todir)

        for directory in os.listdir(self.build_cfg.component_dir()):
            if directory not in ['.xmake.cfg', '.xmake', 'gen', 'import', 'cfg', '.git', '.gitignore', 'target']:
                pathToCopy = os.path.join(self.build_cfg.component_dir(), directory)
                if os.path.isdir(pathToCopy):
                    shutil.copytree(pathToCopy, os.path.join(todir, directory))
                else:
                    shutil.copyfile(pathToCopy, os.path.join(todir, directory))

