sap.ui.define([
  "sap/ui/core/util/MockServer"
], function (MockServer) {
  "use strict";
  return {
    init: function () {
      // create
      var oMockServer = new MockServer({
        rootUri: "/destinations/CATBackendService/CATIssues.svc/"
      }); 
      var oUriParameters = jQuery.sap.getUriParameters();
      // configure
      MockServer.config({
        autoRespond: true,
        autoRespondAfter: oUriParameters.get("serverDelay") || 1000
      });
      // simulate
      var sPath = jQuery.sap.getModulePath("com.sap.cloudscame.CATDashboard.localService");
      oMockServer.simulate(sPath + "/metadata.xml", sPath + "/mockdata");
      // start
      oMockServer.start();
    }
  };
});