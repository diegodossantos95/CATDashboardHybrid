sap.ui.require([
  //Load page objects
  "sap/ui/test/Opa5",
  "com/sap/cloudscame/CATDashboard/test/integration/pages/Common",
  "com/sap/cloudscame/CATDashboard/test/integration/pages/ProjectList",
  "com/sap/cloudscame/CATDashboard/test/integration/pages/ProjectDetail",
  "sap/ui/qunit/qunit-css",
  "sap/ui/thirdparty/qunit",
  "sap/ui/qunit/qunit-junit"
], function (Opa5, Common) {
  "use strict";
  QUnit.config.autostart = false;
    
  Opa5.extendConfig({
    arrangements: new Common(),
    viewNamespace: "com.sap.cloudscame.CATDashboard.view."
  });
    
  sap.ui.require([
    //Load journey objects
    "com/sap/cloudscame/CATDashboard/test/integration/journeys/ProjectListJourney",
    "com/sap/cloudscame/CATDashboard/test/integration/journeys/ProjectDetailJourney"
  ], function () {
    if (!/PhantomJS/.test(window.navigator.userAgent)) {
      QUnit.start();
    }
  });
});