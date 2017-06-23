import os
import stat
import sys

import spi
import logging
import subprocess
import re
import shutil
import glob
import tarfile
import urllib
import contextlib
import tempfile

# TODO: remove this specific import
# it creates a hard link to xmake-core and this can be broken in the future implementation
from phases.deploy import resolve_deployment_credentials

SAP_PYPI_INDEX_SERVER_NAME = 'sap_pypi'

logger = logging.getLogger('buildplugin')


PYPIRC = '''\
[distutils]
index-servers =
    %s

[%s]
%s
%s
%s
'''

USERCUSTOMIZE_PY = '''\
from distutils.config import PyPIRCCommand

def _get_rc_file(self):
    return '%s'

PyPIRCCommand._get_rc_file = _get_rc_file
'''

PYDISTUTILS_CFG = '''\
[global]
verbose = %s

[easy_install]
index_url = %s
'''

PIP_CONF = '''\
[global]
index-url = %s
trusted-host = %s
verbose = %s
'''

VIRTUALENV_INI = '''\
[virtualenv]
no-download = 1
verbose = %s
'''

MANIFEST_IN = '''\
include vendor/*
include *.yml
include *.py
include Procfile
include *.txt
global-include *.cfg
global-exclude .xmake.cfg
'''

ADS_FILE = '''\
artifacts builderVersion:"1.1", {
   group "com.sap.pypi", {
         artifact "%s", {
           file "${gendir}/bundle.tar.gz", extension:"tar.gz", classifier:"bundle"
           %s
         }
   }
}
'''


class BuildPlugin(spi.BuildPlugin):
    def __init__(self, build_cfg):
        spi.BuildPlugin.__init__(self, build_cfg)

        # get import PyPI repository url from xmake
        import_repos = build_cfg.import_repos('PyPi')
        if import_repos is None or len(import_repos) == 0:
            raise Exception('cannot build this project without a PyPI repository. Add it via --import-repo argument')
        if len(import_repos) > 1:
            logger.error('multiple PyPI import repositories found -> ignore all but keep the first one')
        self._import_pypi_repo = import_repos[0]

        # get export PyPI repository url from xmake
        export_repo = build_cfg.export_repo('PyPi')
        self._export_pypi_repo = export_repo

        # few properties
        self._getpip_group_artifact = 'org.python.pypa.download.get-pip:get-pip'
        self._getpip_version = '1478457001'

        self._pypa_home = os.path.join(self.build_cfg.gen_dir(), 'pypa')
        self._virtualenv_home = os.path.join(self.build_cfg.gen_dir(), 'venv')

        if os.name != 'posix':
            self._virtualenv_python = os.path.join(self._virtualenv_home, 'Scripts', 'python.exe')
            self._virtualenv_pip_cmd = (os.path.join(self._virtualenv_home, 'Scripts', 'pip.exe'),)
            self._activate_executable = os.path.join(self._virtualenv_home, 'Scripts', 'activate.bat')
            self._deactivate_executable = os.path.join(self._virtualenv_home, 'Scripts', 'deactivate.bat')
        else:
            self._virtualenv_python = os.path.join(self._virtualenv_home, 'bin', 'python')
            # activate virtualenv no required on linux. Just use the pip/python located in venv/bin directory
            # self._activate_executable = os.path.join(self._virtualenv_home, 'bin', 'activate')

        # self._userhome_dir = os.path.join(self._virtualenv_home, 'home')
        self._userhome_dir = self._virtualenv_home
        if os.name != 'posix':
            self._virtualenvini_dir = os.path.join(self._userhome_dir, 'virtualenv')
        else:
            self._virtualenvini_dir = os.path.join(self._userhome_dir, '.virtualenv')
        self._usercustomize_path = os.path.join(self._userhome_dir, 'usercustomize.py')
        if os.name != 'posix':
            self._pydistutilscfg_path = os.path.join(self._userhome_dir, 'pydistutils.cfg')
        else:
            self._pydistutilscfg_path = os.path.join(self._userhome_dir, '.pydistutils.cfg')
        self._pypirc_path = os.path.join(self._userhome_dir, '.pypirc')
        if os.name != 'posix':
            self._pipcfg_path = os.path.join(self._userhome_dir, 'pip.ini')
        else:
            self._pipcfg_path = os.path.join(self._userhome_dir, 'pip.conf')
        self._virtualenvini_path = os.path.join(self._virtualenvini_dir, 'virtualenv.ini')
        self._copied_src_dir = os.path.join(self.build_cfg.gen_dir(), 'copied_src')
        self._setup_dir = self._copied_src_dir
        if self.build_cfg.alternate_path():
            self._setup_dir = os.path.join(self._copied_src_dir, self.build_cfg.alternate_path())
        self._dependencies_path = os.path.join(self.build_cfg.temp_dir(), 'dependencies')

        # supported plugin options
        self._python_executable = None
        self._option_download_requirements = False
        self._option_skip_tests = False
        self._option_no_linter = False
        self._option_distributions = ['sdist']
        self._option_before_install = None
        self._option_after_install = None
        self._option_before_publish = None

    def set_option(self, option, value):
        '''
            Options are set in file .xmake.cfg a the root dir of the project.
            Below a sample of this file:

            [buildplugin]
            name=python
            download-requirements=true
            skip-tests=true
            no-linter=true
            distributions=sdist,bdist_wheel
        '''
        logger.info('using {}: {}'.format(option, value))
        if option == 'python-executable':
            self._python_executable = value
        elif option == 'download-requirements':
            self._option_download_requirements = value and value.lower() in ('true', 'y', 'yes')
        elif option == 'skip-tests':
            self._option_skip_tests = value and value.lower() in ('true', 'y', 'yes')
        elif option == 'no-linter':
            self._option_no_linter = value and value.lower() in ('true', 'y', 'yes')
        elif option == 'distributions':
            self._option_distributions = value and value.lower().split(',')
            if not self._option_distributions or len(self._option_distributions) == 0 or len([dist for dist in self._option_distributions if dist.startswith('bdist') or dist == 'sdist']) == 0:
                logger.error('distributions option value is not valid. It should be a coma separated list of wheels (ie: sdist,bdist_wheel)')
                logger.error('but you set {}'.format(self._option_distributions))
                logger.error('more information there:')
                logger.error('\thttps://docs.python.org/2/distutils/builtdist.html')
                logger.error('\thttps://packaging.python.org/distributing/#wheels')
                raise Exception('option "distributions" set in .xmake.cfg is not correct')
        elif option == 'before_install':
            self._option_before_install = value and [command.strip() for command in value.split(',')]
        elif option == 'after_install':
            self._option_after_install = value and [command.strip() for command in value.split(',')]
        elif option == 'before_publish':
            self._option_before_publish = value and [command.strip() for command in value.split(',')]
        else:
            logger.warning('unknown build plugin option: {}'.format(option))

    def need_tools(self):
        '''list of tools needed to build target project'''
        return [
            {'toolid': self._getpip_group_artifact, 'version': self._getpip_version, 'type': 'zip'}
        ]

    def run(self):
        logger.info('build in progress...')

        self._copy_sources()

        self._activateVirtualEnv()

        self._before_install()

        self._install()

        self._after_install()

        self._lint_test()

        self._setup_dist()

        self._add_metadata()

        self._create_export_ads_file()

        self._deactivateVirtualEnv()

    # override any of these to get notifications of phase completions
    def after_IMPORT(self, build_cfg):
        # Packages installed in this environment will live under ENV/lib/pythonX.X/site-packages/ https://virtualenv.pypa.io/en/stable/userguide/?highlight=pythonX.X
        self._python_exec_major_minor_version = self._get_python_major_minor_version()

        if not os.path.isdir(self._userhome_dir):
            os.makedirs(self._userhome_dir)

        if not os.path.isdir(self._virtualenvini_dir):
            os.makedirs(self._virtualenvini_dir)

        # creating usercustomize.py file
        with open(self._usercustomize_path, 'w') as f:
            f.write(USERCUSTOMIZE_PY % self._pypirc_path)

        # creating pydistutils.cfg file
        with open(self._pydistutilscfg_path, 'w') as f:
            f.write(PYDISTUTILS_CFG % (('1' if build_cfg.is_tool_debug() else '0'), self._import_pypi_repo))

        # creating .pypirc file without username/password
        with open(self._pypirc_path, 'w') as f:
            f.write(PYPIRC % (
                SAP_PYPI_INDEX_SERVER_NAME,
                SAP_PYPI_INDEX_SERVER_NAME,
                'repository: %s' % self._export_pypi_repo,
                '',
                ''
            ))

        # creating pip.conf file
        with open(self._pipcfg_path, 'w') as f:
            f.write(PIP_CONF % (
                self._import_pypi_repo,
                'nexus.wdf.sap.corp',
                '1' if build_cfg.is_tool_debug() else '0'
            ))

        # creating virtualenv.ini file
        with open(self._virtualenvini_path, 'w') as f:
            f.write(VIRTUALENV_INI % (
                '1' if build_cfg.is_tool_debug() else '0'
            ))

        # set some env variables
        logger.debug('HOME set to {}'.format(self._userhome_dir))
        os.environ['HOME'] = self._userhome_dir
        if os.name != 'posix':
            logger.debug('USERPROFILE set to {}'.format(self._userhome_dir))
            os.environ['USERPROFILE'] = self._userhome_dir
            logger.debug('APPDATA set to {}'.format(self._userhome_dir))
            os.environ['APPDATA'] = self._userhome_dir

        logger.debug('PIP_CONFIG_FILE set to {}'.format(self._pipcfg_path))
        os.environ['PIP_CONFIG_FILE'] = self._pipcfg_path

    def after_DEPLOY(self, build_cfg):
        if not build_cfg.do_deploy():
            return

        # don't publish if we are in staging mode
        if build_cfg.is_release() or build_cfg.get_staging_repoid_parameter():
            return

        self._before_publish(self._setup_dir)

        # upload in PyPI
        self._setup_upload(self._setup_dir)

    def after_CLOSE_STAGING(self, build_cfg):
        if not build_cfg.do_promote():
            return

        # prepare publishable directory
        publishable_dir = os.path.join(self.build_cfg.gen_dir(), 'publishable')
        if os.path.exists(publishable_dir):
            OS_Utils.rm_dir(publishable_dir)
        os.mkdir(publishable_dir)

        # get project name
        setup_dir = self.build_cfg.component_dir()
        if build_cfg.alternate_path():
            setup_dir = os.path.join(setup_dir, self.build_cfg.alternate_path())

        self._activateVirtualEnv(cwd=setup_dir)
        project_name = self._setup_cmd(['--name'], setup_dir)
        self._deactivateVirtualEnv(cwd=setup_dir)

        # download bundle and install it in the to publish directory
        m = re.search(r'^(?P<nexus_base_url>.*)/nexus/', build_cfg.export_repo())
        nexus_base_url = m.group('nexus_base_url')
        self._download_install_bundle_from_nexus(
            nexus_base_url,
            project_name,
            'com.sap.pypi',
            nexus_repo=build_cfg.get_staging_repoid_parameter(),
            dest_directory=publishable_dir
        )

        setup_dir = publishable_dir
        if build_cfg.alternate_path():
            setup_dir = os.path.join(setup_dir, self.build_cfg.alternate_path())

        self._before_publish(setup_dir)

        # upload in PyPI
        self._setup_upload(setup_dir)

    def _create_export_ads_file(self):
        # if we are in staging mode
        if self.build_cfg.is_release() or self.build_cfg.get_staging_repoid_parameter():
            # create bundle file
            project_name = self._setup_cmd(['--name'], self._setup_dir)
            bundle_targz_file = os.path.join(self.build_cfg.gen_dir(), 'bundle.tar.gz')
            with tarfile.open(bundle_targz_file, 'w:gz') as tar:
                tar.add(self._setup_dir, arcname=os.curdir)
            logger.info('created tar of source and dist in {}'.format(bundle_targz_file))

            # list all dist files to deploy in nexus
            artifacts = []
            dist_dir = os.path.join(self._setup_dir, 'dist')
            if os.path.isdir(dist_dir):
                for filename in os.listdir(os.path.join(self._setup_dir, 'dist')):
                    base, ext = os.path.splitext(filename)
                    if ext in ['.gz', '.bz2']:
                        base, pre_ext = os.path.splitext(base)
                        ext = pre_ext + ext
                    if ext:
                        artifacts.append('file "${gendir}/copied_src/dist/%s", extension:"%s"' % (filename, ext[1:]))

            # create ads file
            ads = os.path.join(self.build_cfg.temp_dir(), 'export.ads')
            mapping_script = ADS_FILE % (project_name, '\n'.join(artifacts))
            with open(ads, 'w') as f:
                f.write(mapping_script)
            self.build_cfg.set_export_script(ads)

    def _activateVirtualEnv(self, cwd=None):
        getpip_py = os.path.join(self.build_cfg.tools()[self._getpip_group_artifact][self._getpip_version],
                                 'get-pip.py')

        logger.info('=> installing virtualenv...')
        self._Popen([sys.executable, getpip_py, 'virtualenv', '-t', self._pypa_home], cwd=cwd)

        logger.info('=> creating virtualenv...')
        cmds = [
            sys.executable,
            os.path.join(self._pypa_home, 'virtualenv.py')
        ]
        if self._python_executable:
            cmds.extend(['-p', self._python_executable])
        cmds.append(self._virtualenv_home)
        self._Popen(cmds, cwd=cwd)

        if os.name != 'posix':
            logger.info('=> activating virtualenv venv...')
            self._Popen([self._activate_executable], shellMode=True, cwd=cwd)
        else:
            # activate virtualenv no required on linux. Just use the pip/python located in venv/bin directory
            # self._Popen(["/bin/bash -c \"source " + self._activate_executable + "\""], shellMode=True)
            os.environ['PATH'] = os.path.join(self._virtualenv_home, 'bin') + os.pathsep + os.environ.get('PATH', '')
            # pip issue: Shebang length exceeded in pip executable
            # https://github.com/pypa/virtualenv/issues/596
            self._virtualenv_pip_cmd = (
                self._virtualenv_python,
                os.path.join(self._virtualenv_home, 'lib', 'python' + self._python_exec_major_minor_version, 'site-packages', 'pip')
            )

    def _get_python_major_minor_version(self):
        # get the X.X version from virtualenv python
        python_executable_version = '2.7'
        if self._python_executable:
            output = self._Popen([self._python_executable, "--version"], returnLog=True, cwd='.')
            logger.info('Found Python executable ' + str(self._python_executable) + ' with version: ' + str(output))
            re_compile = re.compile('([0-9]\.[0-9]{1,2})\.[0-9]{1,2}')
            version_ouput = output[0]
            search1 = re_compile.search(version_ouput)
            if search1:
                python_executable_version = search1.group(1)
            else:
                version_ouput = output[1]
                search2 = re_compile.search(version_ouput)
                if search2:
                    python_executable_version = search2.group(1)
                else:
                    logger.warn('Can not find X.X version for custom Python executable')

        logger.info('Extracted version X.X: ' + python_executable_version)
        return python_executable_version

    def _deactivateVirtualEnv(self, cwd=None):
        if os.name != 'posix':
            # deactivate virtualenv no required on linux.
            logger.info('=> deactivate virtualenv')
            self._Popen([self._deactivate_executable], shellMode=True, cwd=cwd)

    def _install(self):
        if not self._option_download_requirements:
            self._pip_install_requirements()
        else:
            logger.info('download requirements rather than installing them. download-requirements option was set')
            self._pip_download_requirements()

    def _lint_test(self):
        if not self._option_no_linter:
            logger.info('=> running linter...')
            self._Popen(list(self._virtualenv_pip_cmd) + [
                'install',
                'setuptools-lint'
            ])

            if self._Popen([self._virtualenv_python, os.path.join(self._setup_dir, 'setup.py'), 'lint'], ignoreError=True, defaultLogLevel=logging.INFO) > 0:
                logger.error('linter fails')
                raise Exception('linter fails')
        else:
            logger.info('linter was not executed as no-linter option was set')

        if not self._option_skip_tests and not self.build_cfg.skip_test():
            logger.info('=> running unit tests...')
            if self._Popen([self._virtualenv_python, os.path.join(self._setup_dir, 'setup.py'), 'test'], ignoreError=True, defaultLogLevel=logging.INFO) > 0:
                logger.error('linter fails')
                raise Exception('linter fails')
        else:
            logger.info('unit tests were not executed as skip-tests option was set')

    def _pip_install_requirements(self):
        requirementsFiles = glob.glob(os.path.join(self._setup_dir, '*requirements.txt'))
        if len(requirementsFiles) > 0:
            for requirementsFile in requirementsFiles:
                logger.info('=> pip install -r {}...'.format(requirementsFile))
                self._Popen(list(self._virtualenv_pip_cmd) + ['install', '-r', requirementsFile])
        else:
            logger.info('=> requirements.txt not found')

        logger.info('=> pip install -e .')
        self._Popen(list(self._virtualenv_pip_cmd) + [
            'install',
            '-e',
            '.'
        ], ignoreError=True)

    def _pip_download_requirements(self):
        def get_install_requires(_requirementsFile):
            global reqs
            with open(_requirementsFile) as reqs_file:
                try:
                    reqs = [_line.rstrip() for _line in reqs_file.readlines()]
                    reqs = reqs[:reqs.index('')]
                except ValueError:
                    logger.debug('requirements.txt is without newline. This is not a problem')
            return reqs
        vendor_dir = os.path.join(self._setup_dir, 'vendor')
        if not os.path.isdir(vendor_dir):
            os.makedirs(vendor_dir)

        # pip download
        requirementsFiles = glob.glob(os.path.join(self._setup_dir, '*requirements.txt'))
        if len(requirementsFiles) > 0:
            for reqFile in requirementsFiles:
                if reqFile[reqFile.rfind(os.sep) + 1:].find('test') < 0:
                    try:
                        logger.info('=> pip download -r {}...'.format(reqFile))
                        self._Popen(list(self._virtualenv_pip_cmd) + [
                            'download',
                            '-d',
                            vendor_dir,
                            '-r',
                            reqFile
                        ])
                    except:
                        logger.warning("Failed to pip download whole file %s, switch to download line by line with ignoring error", reqFile)
                        for line in get_install_requires(reqFile):
                            logger.info('=> pip download -d %s %s', vendor_dir, line)
                            self._Popen(list(self._virtualenv_pip_cmd) + [
                                'download',
                                '-d',
                                vendor_dir,
                                line
                            ], ignoreError=True)
        else:
            logger.info('requirements.txt not found. skipping pip download')

    def _before_install(self):
        if not self._option_before_install:
            return

        for command in self._option_before_install:
            self._setup_cmd([command], self._setup_dir, checkReturnLog=False)

    def _after_install(self):
        if not self._option_after_install:
            return

        for command in self._option_after_install:
            self._setup_cmd([command], self._setup_dir, checkReturnLog=False)

    def _before_publish(self, setup_dir):
        if not self._option_before_publish:
            return

        for command in self._option_before_publish:
            self._setup_cmd([command], setup_dir, checkReturnLog=False)

    def _setup_cmd(self, cmds, setup_dir, checkReturnLog=True):
        results = self._Popen(
            [self._virtualenv_python, '-W', 'ignore', os.path.join(setup_dir, 'setup.py')] + cmds,
            returnLog=True,
            defaultLogLevel=logging.INFO,
            cwd=setup_dir
        )

        if checkReturnLog and len(results) > 1:
            logger.error('\n'.join(results))
            raise Exception('Something goes wrong. Check that all are correctly set in the setup.py file')

        if checkReturnLog:
            return results[0]

    def _setup_dist(self):
        cmd = [self._virtualenv_python, os.path.join(self._setup_dir, 'setup.py')] + self._option_distributions
        self._Popen(cmd)

    def _setup_upload(self, setup_dir):
        try:
            logger.info('=> deploying to PyPI...')

            # creating .pypirc file with username/password filled
            resolve_deployment_credentials(self.build_cfg, 'PyPi')
            with open(self._pypirc_path, 'w') as f:
                f.write(PYPIRC % (
                    SAP_PYPI_INDEX_SERVER_NAME,
                    SAP_PYPI_INDEX_SERVER_NAME,
                    'repository: %s' % self._export_pypi_repo,
                    'username: %s' % self.build_cfg.deploy_user('PyPi'),
                    'password: %s' % self.build_cfg.deploy_password('PyPi')
                ))

            self._activateVirtualEnv(cwd=setup_dir)

            # create MANIFEST.in to include vendor folder
            manifest_file_path = os.path.join(setup_dir, 'MANIFEST.in')
            if not os.path.isfile(manifest_file_path):
                logger.warning('#'*80)
                logger.warning('# {:76} #'.format('your project does not provide any Manifest.in file in root directory'))
                logger.warning('# {:76} #'.format('the build plugin is going to generate a default one'))
                logger.warning('# {:76} #'.format(''))
                logger.warning('# {:76} #'.format('/!\\ WARNING: This functionnality will be removed soon'))
                logger.warning('# {:76} #'.format(''))
                logger.warning('# {:76} #'.format('please provide your own Manifest.in file'))
                logger.warning('# {:76} #'.format('more details there:'))
                logger.warning('# {:76} #'.format('https://docs.python.org/2/distutils/sourcedist.html#the-manifest-in-template'))
                logger.warning('#'*80)
                logger.warning('The file generated to continue deployment:')
                logger.warning('-'*40)
                for manifest_in_line in MANIFEST_IN.split('\n'):
                    if len(manifest_in_line.strip()) > 0:
                        logger.warning('| {:36} |'.format(manifest_in_line.strip()))
                with open(manifest_file_path, 'w') as f:
                    f.write(MANIFEST_IN)
                logger.warning('-'*40)

            cmd = [self._virtualenv_python, os.path.join(setup_dir, 'setup.py')] + self._option_distributions
            cmd.extend([
                'upload',
                '--show-response',
                '-r',
                SAP_PYPI_INDEX_SERVER_NAME
            ])
            self._Popen(cmd, cwd=setup_dir)
            self._deactivateVirtualEnv(cwd=setup_dir)
        finally:
            # if os.path.isfile(self._usercustomize_path):
            #     os.remove(self._usercustomize_path)
            # if os.path.isfile(self._pydistutilscfg_path):
            #     os.remove(self._pydistutilscfg_path)
            if os.path.isfile(self._pypirc_path):
                os.remove(self._pypirc_path)
            # if os.path.isfile(self._pipcfg_path):
            #     os.remove(self._pypirc_path)

    def _add_metadata(self):
        installed_packages = self._Popen(list(self._virtualenv_pip_cmd) + ['list', '--format=freeze'], returnLog=True)
        with open(self._dependencies_path, 'w') as f:
            f.write('\n'.join(installed_packages))
        self.build_cfg.add_metadata_file(self._dependencies_path)

    def _copy_sources(self):
        logger.info('=> copying sources...')

        # clean previous copy
        if os.path.isdir(self._copied_src_dir):
            def onerror(func, path):
                if not os.access(path, os.W_OK):
                    # Is the error an access error ?
                    os.chmod(path, stat.S_IWUSR)
                    func(path)
                else:
                    raise

            shutil.rmtree(self._copied_src_dir, onerror=onerror)
        os.mkdir(self._copied_src_dir)

        # copy current source
        for directory in os.listdir(self.build_cfg.component_dir()):
            if directory not in ['.xmake.cfg', '.xmake', 'gen', 'import', 'cfg', '.git']:
                pathToCopy = os.path.join(self.build_cfg.component_dir(), directory)
                if os.path.isdir(pathToCopy):
                    shutil.copytree(pathToCopy, os.path.join(self._copied_src_dir, directory))
                else:
                    shutil.copyfile(pathToCopy, os.path.join(self._copied_src_dir, directory))

        # change version in file version.txt for taking account of version extension
        if self.build_cfg.version_suffix():
            version_path = os.path.join(self._copied_src_dir, 'version.txt')
            if os.path.isfile(version_path):
                with open(version_path, 'w') as f:
                    f.write('%s-%s' % (self.build_cfg.base_version(), self.build_cfg.version_suffix()))

    def _Popen(self, args, shellMode=False, ignoreError=False, returnLog=False, cwd=None, defaultLogLevel=None):
        logger.info('running {}'.format(' '.join(args)))
        p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=shellMode,
                             env=dict(os.environ), cwd=self._setup_dir if cwd is None else cwd)
        log_lines = []
        for line in p.stdout:
            try:
                line = line.decode('utf-8').encode('ascii', 'ignore')
            except:
                try:
                    line = line.decode('ISO 8859-2').encode('ascii', 'ignore')
                except Exception as e:
                    line = 'WARNING: cannot decode process log line (bad character encoding) %s' % str(e)
            log_lines.append(line.strip())
            self._logGuessLevel(line.strip(), ignoreError=ignoreError, defaultLogLevel=defaultLogLevel)
        rc = p.wait()
        if rc > 0:
            if not ignoreError:
                raise Exception('fails with return code {}'.format(rc))
        return log_lines if returnLog else rc

    @staticmethod
    def _logGuessLevel(msg, defaultLogLevel=None, ignoreError=False):
        logLevel = defaultLogLevel or logging.DEBUG
        logMsg = msg

        m = re.search(r'(?P<level>(?:Could not|No matching))\s', logMsg, re.IGNORECASE)
        if m:
            logLevel = logging.WARNING
        else:
            m = re.search(r'(?P<level>(?:failed|error))\s', logMsg, re.IGNORECASE)
            if m:
                logLevel = logging.WARNING if ignoreError else logging.ERROR

        logger.log(logLevel, logMsg)

    @staticmethod
    def _download_install_bundle_from_nexus(nexus_base_url, artifact_name, group, nexus_repo=None, dest_directory=None):
        if nexus_repo is None or nexus_repo == '':
            raise Exception('cannot get bundle from nexus. Repository is not set')
        if dest_directory is None or dest_directory == '':
            raise Exception('cannot get bundle destination directory is not set')

        url = '{}/nexus/service/local/artifact/maven/content?g={}&a={}&v={}&r={}&c={}&e=tar.gz'.format(
            nexus_base_url,
            group,
            artifact_name,
            'LATEST',
            nexus_repo,
            'bundle'
        )

        try:
            # Download file in temporary directory
            logger.debug('\tdownloading {} bundle from nexus...'.format(artifact_name))
            logger.debug(url)
            tmpFileName = None
            with contextlib.closing(urllib.urlopen(url)) as downloadedFile:
                with tempfile.NamedTemporaryFile(delete=False) as tmpFile:
                    tmpFileName = tmpFile.name
                    shutil.copyfileobj(downloadedFile, tmpFile)
            logger.debug('\t{} bundle downloaded'.format(artifact_name))

            # Untar temporary file in dest_directory
            logger.debug('\tinstalling {} bundle...'.format(artifact_name))
            with tarfile.open(tmpFileName) as tar:
                tar.extractall(path=dest_directory)

            logger.info('\t{} installed'.format(artifact_name))
        except Exception, e:
            logger.exception(e)
            raise Exception('\tcannot download {} {} bundle'.format('LATEST', artifact_name))
