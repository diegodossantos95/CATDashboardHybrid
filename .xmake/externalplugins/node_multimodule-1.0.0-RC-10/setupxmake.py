import os
import externalplugin.autodiscovery
import externalplugin.buildplugin

projectDir = os.path.abspath(os.path.dirname(os.path.realpath('__file__')))


def get_author():
    return 'P&I UxD UXaaS Paris (FR)'


def get_contact_email():
    # DL PI UxD Dev.Studio DevOps Infrastructure <DL_TIP_DFA_FA_INFRASTRUCTURE@exchange.sap.corp>
    return 'DL_TIP_DFA_FA_INFRASTRUCTURE@exchange.sap.corp'


def get_name():
    return 'node_multimodule'


def get_version():
    return '1.0.0'


def get_description():
    return 'External xmake plugin to publish multiple node modules and artifacts'


def get_long_description():
    descFile = os.path.join(projectDir, "README.md")
    if os.path.isfile(descFile):
        with open(descFile, 'r', 'utf-8') as readme:
            return readme.read()
    return ''


def get_project_url():
    return 'https://github.wdf.sap.corp/Norman/DEV_build-xmake-plugin'


def get_discovery_plugin():
    return externalplugin.autodiscovery.AutoDiscovery


def get_plugin():
    return externalplugin.buildplugin.Node_MultiModule
