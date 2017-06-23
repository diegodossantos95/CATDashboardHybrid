import os
import externalplugin.autodiscovery
import externalplugin.buildplugin

projectDir = os.path.abspath(os.path.dirname(os.path.realpath('__file__')))

def get_author():
    return 'Daniel Kullmann'

def get_contact_email():
    return 'daniel.kullmann@sap.com'

def get_name():
    return 'sbt'

def get_version():
    return '1.0.0'

def get_description():
    return 'This is an xmake plugin that allows to build sbt-based Scala projects'

def get_long_description():
    descFile = os.path.join(projectDir, "README.md")
    if os.path.isfile(descFile):
        with open(descFile, 'r', 'utf-8') as readme:
            return readme.read()
    return ''

def get_project_url():
    return 'https://github.wdf.sap.corp/Marmolata/xmake-sbt-plugin'

def get_discovery_plugin():
    return externalplugin.autodiscovery.AutoDiscovery

def get_plugin():
    return externalplugin.buildplugin.BuildPlugin
