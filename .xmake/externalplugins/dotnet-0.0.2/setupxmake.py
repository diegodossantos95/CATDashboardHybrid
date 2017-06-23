import os
import externalplugin.autodiscovery
import externalplugin.buildplugin

projectDir = os.path.abspath(os.path.dirname(os.path.realpath('__file__')))

def get_author():
    return 'Tsvetan Andreev'

def get_contact_email():
    return 'tsvetan.andreev@sap.com'

def get_name():
    return 'dotnet'

def get_version():
    return '0.0.2'

def get_description():
    return 'This is a dotnet xmake plugin'

def get_long_description():
    descFile = os.path.join(projectDir, "README.md")
    if os.path.isfile(descFile):
        with open(descFile, 'r', 'utf-8') as readme:
            return readme.read()
    return ''

def get_project_url():
    return 'https://github.wdf.sap.corp/dtxmake/xmake-dotnet-plugin'

def get_discovery_plugin():
    return externalplugin.autodiscovery.AutoDiscovery

def get_plugin():
    return externalplugin.buildplugin.BuildPlugin
