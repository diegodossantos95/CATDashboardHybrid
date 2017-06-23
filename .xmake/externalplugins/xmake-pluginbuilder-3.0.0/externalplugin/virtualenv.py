import os, sys, imp
import log

def load_source(module_name, module_path):
    module_root_path = os.path.dirname(module_path)
    log.debug('Cleaning the sys modules environment before loading the external plugin to compile')
    removed_modules = _clean_sys_modules()
    log.debug('Done!')
    sys.path.insert(0, module_root_path)
    log.debug('{} loaded'.format(module_path))
    target = imp.load_source(module_name, module_path)
    log.debug('Restoring original sys modules environment')
    log.debug('\t\tCleaning sys modules environment from modules loaded by external plugin to compile')
    _clean_sys_modules()
    log.debug('\t\tDone!')
    sys.path.pop(0)
    _restore_sys_modules(removed_modules)
    log.debug('Done!')
    return target

def _clean_sys_modules():
    removed_modules = []
    for module_name in sys.modules:
        if module_name == 'externalplugin' or module_name.count('setupxmake') >0 or module_name.count('externalplugin.') > 0:
            removed_modules.append({'name': module_name, 'value': sys.modules[module_name]})
    for sys_module in removed_modules:
        log.debug('\t\t{} removed'.format(sys_module['name']))
        del sys.modules[sys_module['name']]
    return removed_modules

def _restore_sys_modules(modules):
    for sys_module in modules:
        log.debug('\t\t{} restored'.format(sys_module['name']))
        sys.modules[sys_module['name']] = sys_module['value']
