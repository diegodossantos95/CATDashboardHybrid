sap.ui.define("com.sap.cloudscame.CATDashboard.test.integration.pages.Common",[
  'sap/ui/test/Opa5'
],function (Opa5) {
  "use strict";

  function getFrameUrl(sHash, sUrlParameters) {
    sHash = sHash || "";
    var sUrl = jQuery.sap.getResourcePath("com/sap/cloudscame/CATDashboard/test", "/mockServer.html");

    if (sUrlParameters) {
      sUrlParameters = "?" + sUrlParameters;
    }

    return sUrl + sUrlParameters + "#" + sHash;
  }

  return Opa5.extend("com.sap.cloudscame.CATDashboard.test.integration.pages.Common", {
    constructor: function (oConfig) {
      Opa5.apply(this, arguments);

      this._oConfig = oConfig;
    },

    iStartMyApp: function (oOptions) {
      var sUrlParameters;
      oOptions = oOptions || {
        delay: 0
      };

      sUrlParameters = "serverDelay=" + oOptions.delay;

      this.iStartMyAppInAFrame(getFrameUrl(oOptions.hash, sUrlParameters));
    },

    iShouldSeeTheText: function (sId, sText) {
      return this.waitFor({
        id: sId,
        success: function (oText) {
          Opa5.assert.strictEqual(oText.getText(), sText);
        }
      });
    },

    iLookAtTheScreen: function () {
      return this;
    }
  });
});