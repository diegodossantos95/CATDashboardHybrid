sap.ui.require([
  'sap/ui/test/Opa5',
  'com/sap/cloudscame/CATDashboard/test/integration/pages/Common',
  'sap/ui/test/actions/Press'
], function (Opa5, Common, Press) {
  "use strict";
  var sViewName = "ProjectDetail";

  Opa5.createPageObjects({
    onProjectDetailPage: {
      baseClass: Common,
      actions: {
        iClickOnCreateIssue: function () {
          return this.waitFor({
            id: "idCreateIssueBtn",
            controlType: "sap.m.Button",
            viewName: sViewName,
            actions: new Press(),
            success: function () {                                
              Opa5.assert.ok(true, "Clicked on Create Issue button");
            },                            
            errorMessage: "Did not find the Create Issue button"
          });                        
        },
        iClickOnEditProject: function () {
          return this.waitFor({
            id: "idEditProjectBtn",
            controlType: "sap.m.Button",
            viewName: sViewName,
            actions: new Press(),
            success: function () {                                
              Opa5.assert.ok(true, "Clicked on Edit Project button");
            },                            
            errorMessage: "Did not find the Edit Project button"
          });                        
        },
        iClickOnEditIssue: function () {
          return this.waitFor({
            controlType: "sap.m.Button",
            viewName: sViewName,
            matchers : new sap.ui.test.matchers.PropertyStrictEquals({
              name : "icon",
              value: "sap-icon://edit"
            }),
            actions: new Press(),
            success: function () {                                
              Opa5.assert.ok(true, "Clicked on Edit Issue button");
            },                            
            errorMessage: "Did not find the Edit Issue button"
          });                        
        }
      },
      assertions: {
        iSeeTheProjectDetail: function () {
          return this.waitFor({
            id: "idProjectDetailsHeader",
            viewName: sViewName,
            success: function () {
              Opa5.assert.ok(true, "Project Detail header is on screen");
            },
            errorMessage: "Did not see Project Detail header"
          });
        },
        iSeeTheCreateIssueDialog: function () {
          return this.waitFor({
            id: "idCreateIssueDialog",
            controlType: "sap.m.Dialog",
            success: function () {
              Opa5.assert.ok(true, "Create Issue dialog is on screen");
            },
            errorMessage: "Did not see Create Issue dialog"
          });
        },
        iSeeTheEditProjectDialog: function () {
          return this.waitFor({
            id: "idEditProjectDialog",
            controlType: "sap.m.Dialog",
            success: function () {
              Opa5.assert.ok(true, "Edit Project dialog is on screen");
            },
            errorMessage: "Did not see Edit Project dialog"
          });
        },
        iSeeTheEditIssueDialog: function () {
          return this.waitFor({
            id: "idEditIssueDialog",
            controlType: "sap.m.Dialog",
            success: function () {
              Opa5.assert.ok(true, "Edit Issue dialog is on screen");
            },
            errorMessage: "Did not see Edit Issue dialog"
          });
        }
      }
    }
  });
});