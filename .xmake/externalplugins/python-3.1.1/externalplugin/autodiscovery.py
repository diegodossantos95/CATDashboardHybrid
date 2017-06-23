import os
import imp
import ast

import spi
import sys
import setupxmake
import logging
import random

logger = logging.getLogger('buildplugin')


class AutoDiscovery(spi.ContentPlugin):

    def __init__(self, build_cfg):
        spi.ContentPlugin.__init__(self, build_cfg)
        # support of --alternate-path argument
        self._setup_dirctory = self.build_cfg.component_dir()
        if self.build_cfg.alternate_path():
            self._setup_dirctory = self.build_cfg.alternate_path()

    # evaluate the component source
    # should return whether it matches the content (true) or not (false).
    def matches(self):
        setup_found = False
        markerFile = os.path.join(self._setup_dirctory, 'setup.py')
        if not os.path.isfile(markerFile):
            return False

        try:
            sys.path.insert(0, self._setup_dirctory)
            fileobj, path, _ = imp.find_module('setup')
            node = ast.parse(fileobj.read(), path, mode='exec')
            for module in ast.walk(node):
                if isinstance(module, ast.Module):
                    for stmt in ast.walk(module):
                        if isinstance(stmt, ast.Expr):
                            if isinstance(stmt.value, ast.Call):
                                if hasattr(stmt.value.func, 'id') and stmt.value.func.id == 'setup':
                                    setup_found = True
                                    # As we don't push the artifact produced to nexus
                                    # May be it is not needed to get the version from setup.py
                                    # for keyword in stmt.value.keywords:
                                    #     if isinstance(keyword.value, ast.Str):
                                    #         self._setup[keyword.arg] = keyword.value.s

            return setup_found
        except:
            logger.warn('found a setup.py but cannot import it to check if setup() method exists')
            logger.warn('so it is not a pip project')

        return False

    # Initialize BuildConfig object with script
    def setup(self):
        if self.matches():
            self.build_cfg._build_script_name = setupxmake.get_name()
            self.build_cfg.set_src_dir(os.path.join(self.build_cfg.component_dir()))

            # get the version from version.txt file
            version_file_path = os.path.join(self._setup_dirctory, 'version.txt')
            if os.path.isfile(version_file_path):
                with open(version_file_path, 'r') as version_file:
                    self.build_cfg.set_base_version(version_file.read().strip())
            else:
                # TODO to remove once we are sure that VERSION file at root directory is the convention to follow
                # We put a temporary version to not break the xmake build
                logger.error('file version.txt not found at the root directory')
                self.build_cfg.set_base_version('0.0.%s-TEMPORARY' % random.randint(1000, 10000))
            return True

        return False
