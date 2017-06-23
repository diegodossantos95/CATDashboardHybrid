artifacts builderVersion:"1.1", {

    version "${buildBaseVersion}", {
        group "${groupId}", {
            artifact "${artifactId}", {
                file "${genroot}/out/Archives-" + "Release" + "/" + "${projectName}" + "-" + "Release" + ".zip", classifier: "Release",  extension: "zip"
		file "${genroot}/out/Exported-IPAs-" + "Release" + "/" + "${schemeName}" + ".ipa", classifier: "Release"
		file "${genroot}/out/" + "${schemeName}" + "-ota.htm", classifier: "Release"

		if ("${DebugFlag}" == "Debug")
		{
			file "${genroot}/out/Archives-" + "Debug" + "/" + "${projectName}" + "-" + "Debug" + ".zip", classifier: "Debug",  extension: "zip"
	                file "${genroot}/out/Exported-IPAs-" + "Debug" + "/" + "${schemeName}" + ".ipa", classifier: "Debug"
        	        file "${genroot}/out/" + "${schemeName}" + "-ota.htm", classifier: "Debug"
		}
		if ("${ExportSrcFlag}" == "True") {
                        file "${genroot}/out/" + "${projectName}" + "_src.zip", classifier: "Src"
                }
            }
        
        }
    }
}
