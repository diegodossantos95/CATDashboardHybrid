import re
import os
import sys
import externalplugin.autodiscovery
import externalplugin.buildplugin

def get_author():
    return 'Marcus Pridham'

def get_contact_email():
    return 'marcus.pridham@sap.com'

def get_name():
    return 'kapsel'

def get_version():
    return '1.0.0'

def get_description():
    return 'xmake plugin for Kapsel'

def get_long_description():
    return 'xmake plugin for Kapsel'

def get_project_url():
    return 'https://github.wdf.sap.corp/MobileSDK/xmake-kapsel-plugin'

def get_discovery_plugin():
    return externalplugin.autodiscovery.AutoDiscovery

def get_plugin():
    return externalplugin.buildplugin.BuildPlugin
