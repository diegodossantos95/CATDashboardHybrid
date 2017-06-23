sap.ui.require([
  "sap/ui/test/opaQunit"
], function (opaTest) {
  "use strict";
  QUnit.module("ProjectList");
    
  opaTest("Should create a new project", function (Given, When, Then) {
        //Start
    Given.iStartMyApp();

        //Actions
    When.onProjectListPage.iLookAtTheScreen().iClickOnCreateProject();

        //Assertions
    Then.onProjectListPage.iSeeTheProjectList().and.iSeeTheCreateProjectDialog().and.iTeardownMyAppFrame();
  });
});