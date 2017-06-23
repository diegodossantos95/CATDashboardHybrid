from artifact import Artifact
from module import Module
import nmlog

import os
import json

from utils import is_existing_file
from xmake_exceptions import XmakeException

# Keys of the configuration file
# 'publish' expects a map whose keys are the folders of the modules to publish.
# The values are the configuration settings for each module. Currently, only shrinkwrap true|false is supported.
# By default, shrinkwrap is true.
MODULES_TO_PUBLISH = "publish"
# 'exports' expects an object whose keys are the artifact names.
# Each key is an object that has 2 properties 'folder' and 'classifier'.
# 'folder' is the relative path from the project's root folder to the folder to tgz.
# 'classifier' has a default value of 'bundle'
ARTIFACTS_TO_EXPORTS = "exports"
FOLDER = "folder"
CLASSIFIER = "classifier"


class ConfigReader(object):
    """Configuration reader for .node_multimodule.json (or .node_multimodule.cfg) files
    Sample file:
    {
        "publish": {
            "client": { "shrinkwrap": true, "lateCheck": true },
            "server": {},
            "test": { "shrinkwrap": false }
        },
        "exports": {
            "node-sap-module1": {
                "folder": "relative/path/from/local/repo/root",
                "classifier": "bundle"
            },
            "node-sap-module2": {
                "folder": "path2"
            }
        }
    }
    """
    def __init__(self, path):
        # full path to the configuration file
        self._path = self.determine_configuration_file(path)
        # contents of the configuration file
        self._json = None
        # modules to npm publish
        self._modules = None
        # artifacts to export
        self._artifacts = None

    def determine_configuration_file(self, path):
        """Uses the .json configuration file if it exists otherwise, switches back to .cfg."""
        configPath = path
        if os.path.isdir(configPath):
            for default_config in [ConfigReader.DEFAULT_CONFIGURATION_FILENAME,
                                   ConfigReader.DEFAULT_CONFIGURATION_FILENAME_OLD]:
                configPath = os.path.join(path, default_config)
                if os.path.exists(configPath):
                    nmlog.info("Using configuration file:", configPath)
                    break
        return configPath

    def load_json(self):
        if not is_existing_file(self._path):
            raise XmakeException("Required configuration file not found! " + self._path)
        with open(self._path, "r") as contents:
            self._json = json.loads(contents.read())

        # For now, the only required property in the configuration file is MODULES_TO_PUBLISH.
        # ARTIFACTS_TO_EXPORTS is optional.
        for key in [MODULES_TO_PUBLISH]:
            if key not in self._json:
                raise XmakeException(self._path + " must contain a root property named " + key)

    def modules_to_publish(self):
        """List of modules to publish."""
        if self._modules is None:
            self._modules = []
            parent_path = os.path.dirname(self._path)
            nmlog.debug("Module parent path", parent_path)
            for module_name, config in self._json[MODULES_TO_PUBLISH].items():
                path = os.path.join(parent_path, str(module_name))
                nmlog.debug("  Module subfolder", str(module_name), "fullpath", path)
                module = Module(path)
                module.parse_config(config)
                if module.do_late_check() is not True:
                    module.check()
                self._modules.append(module)
        return self._modules

    def artifacts_to_export(self):
        if self._artifacts is None:
            # Fill _artifacts only the first time they are requested
            self._artifacts = []
            if ARTIFACTS_TO_EXPORTS in self._json:
                # if the configuration file contains an "exports" property.
                for artifact_name, props in self._json[ARTIFACTS_TO_EXPORTS].iteritems():
                    nmlog.info("Processing artifact:", artifact_name)
                    if FOLDER not in props:
                        raise XmakeException(self._path + " must contain a 'folder' property!")
                    # self._path contains the full path to the configuration file.
                    # We only need its containing folder.
                    actual_path = os.path.join(os.path.dirname(self._path), str(props[FOLDER]))
                    if CLASSIFIER not in props:
                        a = Artifact(artifact_name, actual_path)
                    else:
                        a = Artifact(artifact_name, actual_path, str(props[CLASSIFIER]))
                    self._artifacts.append(a)

        nmlog.info("Number of artifacts to export:", len(self._artifacts))

        return self._artifacts


ConfigReader.DEFAULT_CONFIGURATION_FILENAME = ".node_multimodule.json"
ConfigReader.DEFAULT_CONFIGURATION_FILENAME_OLD = ".node_multimodule.cfg"
