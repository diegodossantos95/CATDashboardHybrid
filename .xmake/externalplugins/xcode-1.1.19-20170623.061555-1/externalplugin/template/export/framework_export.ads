artifacts builderVersion:"1.1", {

    version "${buildBaseVersion}", {
        group "${groupId}", {
            artifact "${artifactId}", {
                file "${genroot}/out/" + "${projectName}" + "-" + "Build-Artfacts" + ".zip", extension: "zip"

            }
		if ("${ExportSrcFlag}" == "True") {
                        file "${genroot}/out/" + "${projectName}" + "_src.zip", classifier: "Src"
                }
        
        }
    }
}
