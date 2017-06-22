sap.ui.define([
  "com/sap/cloudscame/CATDashboard/controller/BaseController",
  "sap/ui/model/Filter"
], function (BaseController, Filter) {
  "use strict";
  return BaseController.extend("com.sap.cloudscame.CATDashboard.controller.ProjectDetail", {
    //------------ VARIABLES ----------------
    _oEditProjectDialog: null,
    _oNewIssueDialog: null,
    _oEditIssueDialog: null,
    _oCreateIssueContext: null,

    //------------ VIEW LIFECYCLE ----------------
    onInit: function () {
      var oRouter = this.getRouter();
      oRouter.getRoute("projectDetail").attachMatched(this._onRouteMatched, this);
    },

    //------------ ACTIONS ----------------
    handleIconTabBarSelect: function (oEvent) {
      var oBinding = this.getView().byId("idIssuesList").getBinding("items"),
        sKey = oEvent.getParameter("key"),
        oFilter;
      if (sKey === "1") {
        oFilter = new Filter("Status", "EQ", "1");
        oBinding.filter([oFilter]);
      } else if (sKey === "2") {
        oFilter = new Filter("Status", "EQ", "2");
        oBinding.filter([oFilter]);
      } else if (sKey === "3") {
        oFilter = new Filter("Status", "EQ", "3");
        oBinding.filter([oFilter]);
      } else {
        oBinding.filter([]);
      }
    },

    onEditIssuePress: function (oEvent) {
      var sPath = oEvent.getSource().getBindingContext("CATModel").getPath();
      this._openEditIssueDialogFragment(sPath);
    },
      
    onCloseIssuePress: function (oEvent) {
      var sPath = oEvent.getSource().getBindingContext("CATModel").getPath();  
      var oIssue = this.getModel("CATModel").getObject(sPath);
      oIssue.Status = 3;
        
      this._updateIssue(sPath, oIssue);
    },
      
    onInProgressIssuePress: function (oEvent) {
      var sPath = oEvent.getSource().getBindingContext("CATModel").getPath();
      var oIssue = this.getModel("CATModel").getObject(sPath);
      oIssue.Status = 2;
        
      this._updateIssue(sPath, oIssue);
    },
      
    onEditProjectPress: function () {
      this._openEditProjectDialogFragment();
    },

    onNewIssuePress: function () {
      this._openNewIssueDialogFragment();
    },

    //------------ EDIT PROJECT DIALOG ----------------
    _openEditProjectDialogFragment: function () {
      if (!this._oEditProjectDialog) {
        this._oEditProjectDialog = sap.ui.xmlfragment("com.sap.cloudscame.CATDashboard.view.EditProject", this);
        this.getView().addDependent(this._oEditProjectDialog);
      }

      this._oEditProjectDialog.open();
    },

    onCancelEditProjectDialog: function () {
      this.getModel("CATModel").resetChanges();
      this._oEditProjectDialog.close();
    },

    onSaveEditProjectDialog: function () {
      this.getModel("CATModel").submitChanges();
      this._oEditProjectDialog.close();
    },

    //------------ NEW ISSUE DIALOG ---------------- 
    _openNewIssueDialogFragment: function () {
      if (!this._oNewIssueDialog) {
        this._oNewIssueDialog = sap.ui.xmlfragment("com.sap.cloudscame.CATDashboard.view.CreateIssue", this);
        this.getView().addDependent(this._oNewIssueDialog);
      }

      var sProjectPath = this.getView().getBindingContext("CATModel").getPath();
      var iProjectId = this.getModel("CATModel").getProperty(sProjectPath + "/Id");
      this._oCreateIssueContext = this.getModel("CATModel").createEntry("/Issues", {
        properties: {
          Name: "",
          Description: "",
          Category: 1,
          Priority: 1,
          Status: 1,
          Project: iProjectId
        }
      });
      this._oNewIssueDialog.setBindingContext(this._oCreateIssueContext, "CATModel");

      this._oNewIssueDialog.open();
    },

    _resetCreateIssueContext: function () {
      this.getModel("CATModel").deleteCreatedEntry(this._oCreateIssueContext);
      this._oCreateIssueContext = null;
    },

    onCancelNewIssueDialog: function () {
      this._resetCreateIssueContext();
      this._oNewIssueDialog.close();
    },

    onSaveNewIssueDialog: function () {
      var oIssue = this._oCreateIssueContext.getObject();
      this._resetCreateIssueContext();

      this.getModel("CATModel").create("/Issues", {
        Name: oIssue.Name,
        Description: oIssue.Description,
        IssuePriorityDetails: {
          Id: oIssue.Priority
        },
        IssueCategoryDetails: {
          Id: oIssue.Category
        },
        IssueStatusDetails: {
          Id: oIssue.Status
        },
        ProjectDetails: {
          Id: oIssue.Project
        }
      });

      this._oNewIssueDialog.close();
    },

    //------------ EDIT ISSUE DIALOG ---------------- 
    _openEditIssueDialogFragment: function (sPath) {
      if (!this._oEditIssueDialog) {
        this._oEditIssueDialog = sap.ui.xmlfragment("com.sap.cloudscame.CATDashboard.view.EditIssue", this);
        this.getView().addDependent(this._oEditIssueDialog);
      }

      this._oEditIssueDialog.bindObject({
        path: sPath,
        model: "CATModel"
      });
      this._oEditIssueDialog.open();
    },

    onCancelEditIssueDialog: function () {
      this.getModel("CATModel").resetChanges();
      this._oEditIssueDialog.close();
    },

    onSaveEditIssueDialog: function () {
      var oContext = this._oEditIssueDialog.getBindingContext("CATModel");
      this._updateIssue(oContext.getPath(), oContext.getObject());

      this._oEditIssueDialog.close();
    },
      
    _updateIssue: function(sPath, oIssue){
      this.getModel("CATModel").update(sPath, {
        Name: oIssue.Name,
        Description: oIssue.Description,
        IssuePriorityDetails: {
          __deferred: {
            uri: "IssuePriorities(" + oIssue.Priority + ")"
          }
        },
        IssueCategoryDetails: {
          __deferred: {
            uri: "IssueCategories(" + oIssue.Category + ")"
          }
        },
        IssueStatusDetails: {
          __deferred: {
            uri: "IssueStatuses(" + oIssue.Status + ")"
          }
        }
      });
    },

    //------------ PRIVATE FUNCTIONS ----------------
    _onRouteMatched: function (oEvent) {
      var oArgs = oEvent.getParameter("arguments");
      this.getView().bindObject({
        path: "/Projects(" + oArgs.id + ")",
        model: "CATModel",
        events: {
          change: this._onBindingChange.bind(this)
        }
      });
    },

    _onBindingChange: function () {
      if (!this.getView().getBindingContext("CATModel")) {
        this.getRouter().getTargets().display("notFound");
      }
    }
  });
});