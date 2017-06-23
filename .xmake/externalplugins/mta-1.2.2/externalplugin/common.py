import re
from os.path import join


def load_yaml(handle):
    doc=dict()
    for line in handle:
        m=re.search("^(\w+)\s*:\s*(.+)",line)
        if m and m.groups>2:
            doc[m.group(1)]=m.group(2)
    return doc

def load_mta(self):
    with open(join(self.build_cfg.component_dir(),"mta.yaml"), 'r') as f:
        doc = load_yaml(f)
        
    if self._mta_extension: 
        with open(join(self.build_cfg.component_dir(),self._mta_extension), 'r') as f:
            ext_doc = load_yaml(f)
            if "ID" in ext_doc:
                if doc and "version" in doc and doc["version"]:
                    ext_doc["version"]=doc["version"]
                return ext_doc            

    return doc

def initialize_src(self):
    doc = load_mta(self)
    if doc and "version" in doc and doc["version"]:
        self.build_cfg.set_base_version(doc["version"].strip())
        if self.build_cfg.version_suffix():
            self.build_cfg.set_version('{}-{}'.format(self.build_cfg.base_version(), self.build_cfg.version_suffix()))
        else:
            self.build_cfg.set_version(self.build_cfg.base_version())
    if doc and "ID" in doc and doc["ID"]:
        self.build_cfg.set_base_artifact(doc["ID"].strip())

    self.build_cfg.set_src_dir(self.build_cfg.component_dir())

