sap.ui.require([
  'sap/ui/test/Opa5',
  'com/sap/cloudscame/CATDashboard/test/integration/pages/Common',
  'sap/ui/test/actions/Press'
], function (Opa5, Common, Press) {
  "use strict";
  var sViewName = "ProjectList";

  Opa5.createPageObjects({
    onProjectListPage: {
      baseClass: Common,
      actions: {
        iClickOnCreateProject: function () {
          return this.waitFor({
            id: "idCreateProjectBtn",
            controlType: "sap.m.Button",
            viewName: sViewName,
            actions: new Press(),
            success: function () {                                
              Opa5.assert.ok(true, "Clicked on Create Project button");
            },                            
            errorMessage: "Did not find the Create Project button"
          });                        
        },
        iClickOnProjectItem: function () {
          return this.waitFor({
            controlType: "sap.m.StandardListItem",
            viewName: sViewName,
            actions: new Press(),
            success: function () {                                
              Opa5.assert.ok(true, "Clicked on Project item");
            },                            
            errorMessage: "Did not find the Project item"
          });                        
        }
      },
      assertions: {
        iSeeTheProjectList: function () {
          return this.waitFor({
            id: "idProjectList",
            viewName: sViewName,
            success: function () {
              Opa5.assert.ok(true, "Projects list is on screen");
            },
            errorMessage: "Did not see Projects list"
          });
        },
        iSeeTheCreateProjectDialog: function () {
          return this.waitFor({
            id: "idCreateProjectDialog",
            controlType: "sap.m.Dialog",
            success: function () {
              Opa5.assert.ok(true, "Create Project dialog is on screen");
            },
            errorMessage: "Did not see Create Project dialog"
          });
        }
      }
    }
  });
});