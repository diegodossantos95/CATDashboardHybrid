sap.ui.define([
  "com/sap/cloudscame/CATDashboard/controller/BaseController",
  "sap/ui/model/Filter"
], function (BaseController, Filter) {
  "use strict";
  return BaseController.extend("com.sap.cloudscame.CATDashboard.controller.ProjectList", {
    //------------ VARIABLES ----------------
    _oCreateProjectDialog: null,
    _oCreateProjectContext: null,

    //------------ VIEW LIFECYCLE ----------------
    onInit: function () {
    },

    //------------ ACTIONS ----------------
    onSearchProjectList: function (oEvent) {
      var aFilters = [];
      var sQuery = oEvent.getParameter("query");
      var oProjectList = this.getView().byId("idProjectList");
      var oBinding = oProjectList.getBinding("items");

      if (sQuery && sQuery.length > 0) {
        var oFilter = new Filter("Name", "Contains", sQuery);
        aFilters.push(oFilter);
      }

      oBinding.filter(aFilters);
    },
      
    onItemPress: function (oEvent) {
      var sPath = oEvent.getParameter("listItem").getBindingContextPath();
      var sId = this.getModel("CATModel").getProperty(sPath + "/Id");
      this.getRouter().navTo("projectDetail", {
        id: encodeURIComponent(sId)
      });
    },

    onCreateProjectPress: function () {
      if (!this._oCreateProjectDialog) {
        this._oCreateProjectDialog = sap.ui.xmlfragment("com.sap.cloudscame.CATDashboard.view.CreateProject", this);
        this.getView().addDependent(this._oCreateProjectDialog);
      }
      
      this._oCreateProjectContext = this.getModel("CATModel").createEntry("/Projects", { 
        properties: { 
          Name: "", 
          StartDate: new Date(), 
          EndDate: new Date()
        } 
      });
      this._oCreateProjectDialog.setBindingContext(this._oCreateProjectContext, "CATModel");
      this._oCreateProjectDialog.open();
    },
      
    //------------ CREATE PROJECT DIALOG ----------------
    onCancelNewProjectDialog: function () {
      this.getModel("CATModel").deleteCreatedEntry(this._oCreateProjectContext);
      this._oCreateProjectDialog.close();
    },
        
    onSaveNewProjectDialog: function () {
      this.getModel("CATModel").submitChanges();
      this._oCreateProjectDialog.close(); 
    }
  });
});