sap.ui.require([
  "sap/ui/test/opaQunit"
], function (opaTest) {
  "use strict";
  QUnit.module("ProjectDetail");
    
  opaTest("Should see the Project Detail view", function (Given, When, Then) {
        //Start
    Given.iStartMyApp();

        //Actions
    When.onProjectListPage.iLookAtTheScreen().iClickOnProjectItem();

        //Assertions
    Then.onProjectDetailPage.iSeeTheProjectDetail().and.iTeardownMyAppFrame();
  });
    
  opaTest("Should create a new issue", function (Given, When, Then) {
        //Start
    Given.iStartMyApp();

        //Actions
    When.onProjectListPage.iLookAtTheScreen().iClickOnProjectItem();
    When.onProjectDetailPage.iClickOnCreateIssue();

        //Assertions
    Then.onProjectDetailPage.iSeeTheProjectDetail().and.iSeeTheCreateIssueDialog().and.iTeardownMyAppFrame();
  });
    
  opaTest("Should edit the project", function (Given, When, Then) {
        //Start
    Given.iStartMyApp();

        //Actions
    When.onProjectListPage.iLookAtTheScreen().iClickOnProjectItem();
    When.onProjectDetailPage.iClickOnEditProject();

        //Assertions
    Then.onProjectDetailPage.iSeeTheProjectDetail().and.iSeeTheEditProjectDialog().and.iTeardownMyAppFrame();
  });
    
  opaTest("Should edit the issue", function (Given, When, Then) {
        //Start
    Given.iStartMyApp();

        //Actions
    When.onProjectListPage.iLookAtTheScreen().iClickOnProjectItem();
    When.onProjectDetailPage.iClickOnEditIssue();

        //Assertions
    Then.onProjectDetailPage.iSeeTheProjectDetail().and.iSeeTheEditIssueDialog().and.iTeardownMyAppFrame();
  });
});