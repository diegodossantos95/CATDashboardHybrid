import json
from os.path import join

import nmlog

# xmake dependencies
import spi
import setupxmake
from utils import is_existing_file
from xmake_exceptions import XmakeException


class AutoDiscovery(spi.ContentPlugin):
    def __init__(self, build_cfg):
        spi.ContentPlugin.__init__(self, build_cfg)

    def has_priority_over_plugins(self):
        """Here the list of xmake plugins that are in conflict with this plugin.
        None, as this plugin cannot be auto discovered."""
        return ()

    def matches(self):
        """This plugin can never match, you have to specify its use in xmake.cfg."""
        return False

    def get_version(self):
        """Reads and returns the version from the package.json file found in the project's root folder.

        :returns The project's root package.json version value
        """
        package_file = join(self.build_cfg.component_dir(), "package.json")
        if not is_existing_file(package_file):
            raise XmakeException("package.json required in project's root folder")
        with open(package_file, "r") as contents:
            package_json = json.load(contents)
        if "version" not in package_json:
            raise XmakeException('package.json must contain a version!')
        version = str(package_json["version"])
        nmlog.debug('Root package.json version:', version)
        return version

    def setup(self):
        """Initialize BuildConfig object with script"""
        nmlog.debug('setup phase!')
        self.build_cfg._build_script_name = setupxmake.get_name()
        self.build_cfg.set_base_version(self.get_version())
        self.build_cfg.set_src_dir(self.build_cfg.component_dir())
        return True
