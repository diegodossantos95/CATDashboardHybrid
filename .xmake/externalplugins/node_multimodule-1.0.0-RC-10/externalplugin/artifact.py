import os
import textwrap
import tarfile

# xmake imports
import nmlog

# Default classifier value
BUNDLE = "bundle"
# Generated TGZ file name
BUNDLE_TGZ = "bundle.tgz"
# Template for the export.ads file
EXPORT_ADS_FILE = '''artifacts builderVersion:"1.1", {{
    group "com.sap.npm", {{{artifacts}
    }}
}}
'''
# Template for each one of the 'artifacts' from EXPORT_ADS_FILE
ARTIFACT_GROUP = '''
        artifact "{artifact_name}", {{
            file "{artifact_file}", extension: "tgz", classifier: "{classifier}"
        }}'''


class Artifact(object):
    """
    Artifact class, that defines ... an artifact.
    Artifacts will be exported to Nexus thanks to the export.ads file.
    """
    def __init__(self, name, folder, classifier=BUNDLE):
        """Artifact constructor.

        :param name: Te name of the artifact to export
        :param folder: The folder to tgz
        :param classifier: The classifier of the artifact. Bundle by default.
        """
        self._name = name
        self._folder = folder
        self._classifier = classifier
        self._bundle_tgz_name = BUNDLE_TGZ
        nmlog.debug("Artifact", self._name, "(", self._classifier, ") in folder:", self._folder)

    def get_name(self):
        return self._name

    def get_folder(self):
        return self._folder

    def get_classifier(self):
        return self._classifier

    def get_bundle_tgz_name(self):
        return self._bundle_tgz_name

    def export(self):
        nmlog.debug('tgz will be located in folder', self.get_folder())
        nmlog.info('Opening bundle tar gz', self.get_bundle_tgz_name())
        output_filename = os.path.join(self.get_folder(), self.get_bundle_tgz_name())
        with tarfile.open(output_filename, "w:gz") as tgz:
            tgz.add(self.get_folder(), arcname=self.get_name())

    def get_export_artifact(self):
        """Gets the artifact 'group' text for this artifact.

        :returns: The text lines representing the artifact group of the export.ads file for this artifact
        """
        artifact_file = os.path.join(self.get_folder(), self.get_bundle_tgz_name())

        artifact = ARTIFACT_GROUP

        return artifact.format(artifact_name=self.get_name(), artifact_file=artifact_file,
                               classifier=self.get_classifier())

    @staticmethod
    def get_export_ads_file(artifacts):
        """Static function that generates the export.ads files given an array of packages.

          :param artifacts: The list of artifacts (instances of this class) to add to the export.ads file,
          to be exported to nexus.
        """
        export_ads = textwrap.dedent(EXPORT_ADS_FILE)
        export_ads_artifacts = ''
        for index, module in enumerate(artifacts):
            export_ads_artifacts += module.get_export_artifact()

        file_contents = export_ads.format(artifacts=export_ads_artifacts)
        nmlog.debug('---------EXPORT.ADS---------------')
        nmlog.debug(file_contents)
        nmlog.debug('---------/EXPORT.ADS--------------')
        return file_contents
