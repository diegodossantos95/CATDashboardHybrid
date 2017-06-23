import os
from os.path import join

import nmlog
from artifact import Artifact
from configreader import ConfigReader

from node import build as OfficialNode

# xmake dependencies
from xmake_exceptions import XmakeException
from config import NPMREPO
from phases.deploy import resolve_deployment_credentials


class Node_MultiModule(OfficialNode):
    def __init__(self, build_cfg):
        OfficialNode.__init__(self, build_cfg)
        nmlog.info('This is the multi module plugin for BUILD')
        self._modules = None
        self._artifacts = None

    def set_option(self, o, v):
        if o == 'colored_logs':
            if v:
                nmlog.colored_logs()
                nmlog.info('Using colored logs')
            else:
                nmlog.info('Using standard logs')
            return
        # Option not handled, let the copy of the official node.py plugin handle it
        OfficialNode.set_option(self, o, v)

    # list of tools needed to build target project
    def need_tools(self):
        # the official node.py sets the requested nodejs version in _nodejs_version
        return [{'toolid': 'com.sap.prd.distributions.org.nodejs.linuxx86_64:nodejs',
                 'type': 'tar.gz',
                 'version': self._node_version}]

    def get_modules(self):
        """The list of all modules passed in the 'publish' property of the .node_multimodule.json (or .node_multimodule.cfg)
         configuration file."""
        return self._modules

    def get_artifacts(self):
        """The list of all artifacts passed in the 'exports' property of the .node_multimodule.json (or .node_multimodule.cfg)
         configuration file. Their bundle.tgz files will be exported to Nexus."""
        return self._artifacts

    def get_output_module_folder(self, module):
        return join(self.module_dir, module.get_module_path())

    def multi_module_npm(self, module, parameters, repo=None):
        """Changes the current working directory for a single npm command.

        :param module: The module for which the command must be performed
        :param parameters: Array of parameters to pass to npm.
        :param repo: The registry to use (--reg parameter).
        """
        # save current working dir
        save_cwd = self._env.cwd
        try:
            cwd = self.get_output_module_folder(module)
            nmlog.debug('########################### NPM COMMAND ###########################')
            nmlog.debug('CWD=', cwd)
            nmlog.debug('RUN> npm', parameters)
            nmlog.debug('########################### NPM COMMAND ###########################')
            self._env.cwd = cwd
            OfficialNode.npm(self, parameters, repo)
        finally:
            # restore official cwd
            self._env.cwd = save_cwd

    def npm_shrinkwrap(self, module):
        self.multi_module_npm(module, ["shrinkwrap", "--production"])

    def npm_publish(self, module, repo):
        self.multi_module_npm(module, ["publish"], repo)

    def multi_publish(self, repo):
        modules = self.get_modules()
        if modules is None:
            modules = []
        for module in modules:
            nmlog.debug('Processing module', module.get_module_name)
            if module.do_late_check() is True:
                module.check()
            # no publish, no shrinkwrap for private modules
            if not module.is_private():
                # no shrinkwrap if disabled by configuration
                if module.do_shrinkwrap():
                    self.npm_shrinkwrap(module)
                self.npm_publish(module, repo)

    # Override copy of official node.py plugin
    def prepare_sources(self):
        OfficialNode.prepare_sources(self)
        self.load_plugin_config()

    def load_plugin_config(self):
        """Read the configuration from the .node_multimodule.json (or .node_multimodule.cfg) file"""
        # This is a shameless copy of self.module_dir that is not yet defined
        config_path = join(self.build_cfg.gen_dir(), 'module')
        nmlog.debug('Reading plugin configuration from ', config_path)
        config = ConfigReader(config_path)
        config.load_json()
        self._modules = config.modules_to_publish()
        self._artifacts = config.artifacts_to_export()

    # Main, Override from OfficialNode
    def run(self):
        nmlog.info('Build in progress...')
        OfficialNode.run(self)
        nmlog.info('Build done!')

    # Override copy of official node.py plugin
    def prepare_deployment(self):
        """Creates all the bundle.tgz for the nexus deployment."""
        artifacts = self.get_artifacts()
        if artifacts is None:
            artifacts = []
        for artifact in artifacts:
            artifact.export()

    # Override copy of official node.py plugin
    def publish(self):
        repo = self.build_cfg.export_repo(NPMREPO)
        if repo is None:
            raise XmakeException("no NPM deployment repository configured")
        nmlog.info("node_multimodule: publishing to NPM repository " + repo + "...")
        resolve_deployment_credentials(self.build_cfg, NPMREPO)
        user = self.build_cfg.deploy_user(NPMREPO)
        password = self.build_cfg.deploy_password(NPMREPO)
        if user is None:
            raise XmakeException("no user found for NPM deployment")
        if password is None:
            raise XmakeException("no password found for NPM deployment")
        nmlog.info("  using user " + user)
        try:
            OfficialNode.prepare_npmrc(self, user, password)
            self.multi_publish(repo)
        finally:
            if self._npmrc_file is not None:
                os.remove(self._npmrc_file)

    # Override copy of official node.py plugin
    def prepare_export(self):
        pass

    # Override copy of official node.py plugin
    def gather_dependencies(self):
        """This is the function in which the official node.py plugin does the shrinkwrap. We have to override it."""
        pass

    # Override copy of official node.py plugin
    def after_PRELUDE(self, build_cfg):
        OfficialNode.after_PRELUDE(self, build_cfg)

    def after_MODULES(self, build_cfg):
        OfficialNode.after_MODULES(self, build_cfg)

    def after_IMPORT(self, build_cfg):
        OfficialNode.after_IMPORT(self, build_cfg)

    def after_BUILD(self, build_cfg):
        OfficialNode.after_BUILD(self, build_cfg)
        ads = join(self.build_cfg.temp_dir(), "export.ads")
        if self.build_cfg.skip_build():
            self.load_plugin_config()
        mapping_script = Artifact.get_export_ads_file(self.get_artifacts())
        with open(ads, 'w') as f:
            f.write(mapping_script)
            self.build_cfg.set_export_script(ads)

    def after_EXPORT(self, build_cfg):
        OfficialNode.after_EXPORT(self, build_cfg)

    # Override copy of official node.py plugin
    def after_DEPLOY(self, build_cfg):
        OfficialNode.after_DEPLOY(self, build_cfg)

    def after_PROMOTE(self, build_cfg):
        OfficialNode.after_PROMOTE(self, build_cfg)

    def after_FORWARD(self, build_cfg):
        OfficialNode.after_FORWARD(self, build_cfg)
