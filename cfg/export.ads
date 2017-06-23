artifacts builderVersion:"1.1", {
    group "${groupId}", {
	artifact "${artifactId}",isVariant:true, {
	    file "${file}", classifier: "${classifierId}"
			if ( buildRuntime=="darwinintel64" ) {
				file "${otafile}", classifier: "release-ota", extension: "htm"
			}
		}
    }
 }
