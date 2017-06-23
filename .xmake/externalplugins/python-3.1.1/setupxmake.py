import os
import externalplugin.autodiscovery
import externalplugin.buildplugin

projectDir = os.path.abspath(os.path.dirname(os.path.realpath('__file__')))


def get_author():
    return 'Nay Lin Aung, Bui Nguyen Thang, Camel Aissani'


def get_contact_email():
    return 'xmake-support@exchange.sap.corp'


def get_name():
    return 'python'


def get_version():
    return '3.1.1'


def get_description():
    return 'build plugin for python projects'


def get_long_description():
    return 'build plugin for python projects'


def get_project_url():
    return 'https://github.wdf.sap.corp/dtxmake/xmake-python-plugin'


def get_discovery_plugin():
    return externalplugin.autodiscovery.AutoDiscovery


def get_plugin():
    return externalplugin.buildplugin.BuildPlugin
