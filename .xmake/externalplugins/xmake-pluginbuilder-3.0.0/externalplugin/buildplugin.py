import imp, zipfile, tarfile, glob, shutil, os, subprocess
import xmake_exceptions, spi, log
import virtualenv

class BuildPlugin(spi.BuildPlugin):

    def __init__(self, build_cfg):
        spi.BuildPlugin.__init__(self, build_cfg)

    def set_option(self,o,v):
        log.warning("unknown build plugin option; "+o)

    def run(self):
        log.info('Build in progress...')

        # Clean gen dir
        log.info('\tclean %s...' % self.build_cfg.gen_dir())
        if os.path.exists(self.build_cfg.gen_dir()):
            shutil.rmtree(self.build_cfg.gen_dir())

        # Run unit tests
        if not self.build_cfg.skip_test():
            log.info('\tstarting tests...')
            test_path = os.path.join(self.build_cfg.src_dir(), 'tests', 'test.py')
            p = subprocess.Popen(['python', test_path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=dict(os.environ), cwd=None)
            for line in p.stdout:
                log.info(line)
            rc = p.wait()
            if rc > 0: raise xmake_exceptions.XmakeException("ERR: python %s returned %s" % (test_path, str(rc)))

        # Compute and write version.txt and sourceversion.txt
        if not os.path.exists(self.build_cfg.gen_dir()):
            os.mkdir(self.build_cfg.gen_dir())
        version_path = os.path.join(self.build_cfg.gen_dir(), 'version.txt')
        sourceversion_path = os.path.join(self.build_cfg.gen_dir(), 'sourceversion.txt')
        log.info('\tgenerate %s and %s' % (version_path, sourceversion_path))
        with open(sourceversion_path, 'w') as f:
            p = subprocess.Popen(['git', 'rev-parse', 'HEAD'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=dict(os.environ), cwd=None)
            for line in p.stdout:
                f.write(line)
            rc = p.wait()
            if rc > 0: raise xmake_exceptions.XmakeException("ERR: git rev-parse HEAD returned %s" % str(rc))
        with open(version_path, 'w') as f:
                f.write(self.build_cfg.version())

        # Create package
        target_setupxmake = virtualenv.load_source('target_setupxmake', os.path.join(self.build_cfg.src_dir(), 'setupxmake.py'))
        plugin_name = target_setupxmake.get_name()
        dist = os.path.join(self.build_cfg.gen_dir(), 'inst')
        zip_path = os.path.join(dist, plugin_name+'.zip')
        targz_path = os.path.join(dist, plugin_name+'.tar.gz')
        log.info('\tgenerate %s and %s...' % (zip_path, targz_path))
        os.makedirs(dist)
        zf = zipfile.ZipFile(zip_path, 'w')
        tar = tarfile.open(targz_path, 'w:gz')
        os.chdir(self.build_cfg.src_dir())
        for root, dirs, files in os.walk(self.build_cfg.src_dir()):
            if root.endswith('tests') or root.endswith('xmake-stub'):
                continue
            for fn in files:
                if fn.endswith('.pyc'):
                    continue
                absfn = os.path.join(root, fn)
                relfn = absfn[len(self.build_cfg.src_dir())+len(os.sep):]
                zf.write(absfn, relfn)
                tar.add(relfn)
        zf.write(version_path, 'version.txt')
        zf.write(sourceversion_path, 'sourceversion.txt')
        os.chdir(self.build_cfg.gen_dir())
        tar.add('version.txt')
        tar.add('sourceversion.txt')
        zf.close()
        tar.close()

        # Generate ADS file
        ads_path = os.path.join(self.build_cfg.temp_dir(), 'export.ads')
        log.info('\tgenerate %s...' % ads_path)
        with open(ads_path, 'w') as f:
            f.write('artifacts builderVersion:"1.1", {\n')
            f.write('\tgroup "com.sap.prd.xmake.buildplugins", {\n')
            f.write('\t\tartifact "%s", {\n' % plugin_name)
            f.write('\t\t\tfile "${gendir}/inst/%s.zip"\n' % plugin_name)
            f.write('\t\t\tfile "${gendir}/inst/%s.tar.gz", extension:"tar.gz"\n' % plugin_name)
            f.write('\t\t}\n')
            f.write('\t}\n')
            f.write('}\n')
        self.build_cfg.set_export_script(ads_path)

        log.info('Build done!')

    # override any of these to get notifications of phase completions
    def after_PRELUDE(self, build_cfg): pass
    def after_MODULES(self, build_cfg): pass
    def after_IMPORT(self, build_cfg): pass
    def after_BUILD(self, build_cfg): pass
    def after_EXPORT(self, build_cfg): pass
    def after_DEPLOY(self, build_cfg): pass
    def after_PROMOTE(self, build_cfg): pass
    def after_FORWARD(self, build_cfg): pass
