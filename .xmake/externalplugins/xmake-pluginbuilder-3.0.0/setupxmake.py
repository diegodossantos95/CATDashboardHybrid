import re
import os
import externalplugin.autodiscovery
import externalplugin.buildplugin

projectDir = os.path.abspath(os.path.dirname(os.path.realpath('__file__')))

def get_author():
    return 'Jean Maqueda'

def get_contact_email():
    return 'jean.maqueda@sap.com'

def get_name():
    return 'xmake-pluginbuilder'

def get_version():
    return '3.0.0'

def get_description():
    return 'build plugin which builds xmake plugin'

def get_long_description():
    descFile = os.path.join(projectDir, "README.rst")
    if os.path.isfile(markerFile):
        with open(descFile, 'r', 'utf-8') as readme:
            return readme.read()
    return ''

def get_project_url():
    return 'https://github.wdf.sap.corp/dtxmake/xmake-pluginbuilder-plugin'

def get_discovery_plugin():
    return externalplugin.autodiscovery.AutoDiscovery

def get_plugin():
    return externalplugin.buildplugin.BuildPlugin
