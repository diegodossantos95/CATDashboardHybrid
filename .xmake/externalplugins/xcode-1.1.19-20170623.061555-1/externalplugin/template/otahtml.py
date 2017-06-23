OTA_INSTALL_PAGE_HTML = """\
	<html>
            <head>
                    <title>OTA Install Page</title>
                    <meta name="scm-type" content="git">
                    <meta name="repo" content="ssh://git.wdf.sap.corp:29418/prod/iOS/main.git">
                    <meta name="branch" content="ota-service-sap-template">
                    <style>
                            .buildInfo {
                                    font-family: sans-serif;
                                    font-size: 7pt;
                                    color: grey;
                                    border-style:none;
                            }
                    </style>
            </head>
            <body>

	<script language="javascript" type="text/javascript">
		debugger;
		var thisUrl = document.location; 
		var htmlUrl = "https://apple-ota.wdf.sap.corp:8443/ota-service/HTML?title=@otaappname@&bundleIdentifier=@otabundleid@&bundleVersion=@otaversion@&ipaClassifier=@ipaClassifier@&otaClassifier=@otaClassifier@"          
		document.location.href= htmlUrl+"&Referer="+encodeURIComponent(thisUrl);        
	</script>


    <br/>
    </body>
    </html>
			"""
REDIRECT_HTML = """\
			<html>
					<head>
						<meta http-equiv="refresh" content="0; URL=@otalink@">
						<body>You will be redirected within the next few seconds.<br />In case this does not work click <a href="@otalink@">here</a></body>
			</html>
			"""
ANDROID_REDIRECT_HTML = """\
			<html>
					<head>
						<meta http-equiv="refresh" content="0; URL=@otalinkandroid@">
						<body>You will be redirected within the next few seconds.<br />In case this does not work click <a href="@otalinkandroid@">here</a></body>
			</html>
			"""
