import json
from os.path import join

import nmlog
# xmake dependencies
from utils import is_existing_file
from xmake_exceptions import XmakeException


class Module:
    """
    Module class that describes a node module.
    Modules will be npm publish-ed.

    Contains information about:
    - the module name
    - the path of the package.json file
    - the contents of the package.json file
    """

    def __init__(self, path):
        """ctor.

        :param path: This module's relative path from the root directory
        """
        # Relative path to the package.json file of the module
        self._path = path
        # True if the package.json file is marked private
        self._is_private = False
        # The contents of the file
        self._package_json = None
        # module name will be read from package.json
        self._module_name = ''
        # By default, perform the shrinkwrap --production before publish
        self._do_shrinkwrap = True
        # By default, make sure the modules to publish exist when the plugin is loaded. If True,
        # this check is done at publish time.
        self._late_check = False

    def check(self):
        """Verifies that the module is correctly defined and sets up some properties by
        reading the contents of the package.json file."""
        json_file = self._path
        if not json_file.lower().endswith("package.json"):
            json_file = join(json_file, "package.json")

        if not is_existing_file(json_file):
            raise XmakeException('package.json not found: ' + json_file)

        with open(json_file, "r") as d:
            self._package_json = json.load(d)

        if "name" not in self._package_json:
            raise XmakeException(json_file + ' must contain a name field')

        self._module_name = self._package_json["name"]
        nmlog.info('Using module', self.get_module_name())

        if "private" in self._package_json:
            if self._package_json["private"] is True:
                self._is_private = True
                # If a package.json is private, don't check anything else
                nmlog.info(json_file + ' file is marked as private')
                return

    def get_module_name(self):
        """The name of the module, found in the package.json."""
        return self._module_name

    def get_module_path(self):
        """The path to the folder in which the module is located, relative to the project's root in the gen folder."""
        return self._path

    def is_private(self):
        """True if the module is private."""
        return self._is_private

    def do_shrinkwrap(self):
        """True is shrinkwrap must be performed."""
        return self._do_shrinkwrap

    def do_late_check(self):
        """True if the modules to publish must be checked at a late stage (publish) in the build,
        instead of at the loading of the plugin."""
        return self._late_check

    def parse_config(self, config):
        """Sets properties to the module by reading its configuration under the "publish" node
        of the .node_multimodule.json (or .node_multimodule.cfg) file.

        :param config: The configuration object of this module, under the "publish" node of
         the .node_multimodule.json (or .node_multimodule.cfg) file.
        """
        if config:
            if "shrinkwrap" in config:
                self._do_shrinkwrap = config["shrinkwrap"]
            if "lateCheck" in config:
                self._late_check = config["lateCheck"]
