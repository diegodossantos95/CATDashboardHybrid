artifacts builderVersion:"1.1", {

    version "${buildBaseVersion}", {
        group "${groupId}", {
            artifact "${artifactId}", {
                file "${genroot}/out/Archives-Release-iphoneos"  + "/" + "${schemeName}" + "-" + "Release" + ".zip", classifier: "Release",  extension: "zip"
	
		if ("${DebugFlag}" == "Debug") 
		{ 
			file "${genroot}/out/Archives-Debug-iphoneos" + "/" + "${schemeName}" + "-" + "Debug" + ".zip", classifier: "Debug",  extension: "zip"
		}
		if ("${ExportSrcFlag}" == "True") {
                        file "${genroot}/out/" + "${projectName}" + "_src.zip", classifier: "Src"
                }
        
        }
    }
  }
}
