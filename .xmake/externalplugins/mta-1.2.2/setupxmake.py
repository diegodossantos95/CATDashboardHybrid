import re, os, sys
projectDir = os.path.dirname(os.path.dirname(os.path.realpath('__file__')))
sys.path.append(projectDir)
import externalplugin.autodiscovery, externalplugin.buildplugin

def get_author():
    return 'Production Team Levallois'

def get_contact_email():
    return 'DL PI_Tech_EngSrv_Production_Paris'

def get_name():
    return 'mta'

def get_version():
    return '1.2.2'

def get_description():
    return 'MTA plugin for xMake'

def get_long_description():
    descFile = os.path.join(projectDir, "README.md")
    if os.path.isfile(markerFile):
        with open(descFile, 'r', 'utf-8') as readme:
            return readme.read()
    return ''

def get_project_url():
    return 'https://github.wdf.sap.corp/dtxmake/xmake-mta-plugin'

def get_discovery_plugin():
    return externalplugin.autodiscovery.AutoDiscovery

def get_plugin():
    return externalplugin.buildplugin.BuildPlugin
