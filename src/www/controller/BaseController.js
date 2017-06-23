sap.ui.define([
  "sap/ui/core/mvc/Controller",
  "com/sap/cloudscame/CATDashboard/model/formatter",
  "sap/ui/core/routing/History"
], function(Controller, formatter, History) {
  "use strict";

	/*
        Common base class for the controllers of this app containing some convenience methods
    */
  return Controller.extend("com.sap.cloudscame.CATDashboard.controller.BaseController", {

    formatter: formatter,
		/**
		 * Convenience method for accessing the router in each controller of the application.
		 * @public
		 * @returns {sap.ui.core.routing.Router} the router for this component
		 */
    getRouter: function() {
      return this.getOwnerComponent().getRouter();
    },

		/**
		 * Convenience method for getting the view model by name in every controller of the application.
		 * @public
		 * @param {string} sName the model name
		 * @returns {sap.ui.model.Model} the model instance
		 */
    getModel: function(sName) {
      return this.getView().getModel(sName) || this.getOwnerComponent().getModel(sName);
    },


		/**
		 * Convenience method for setting the view model in every controller of the application.
		 * @public
		 * @param {sap.ui.model.Model} oModel the model instance
		 * @param {string} sName the model name
		 * @returns {sap.ui.mvc.View} the view instance
		 */
    setModel: function(oModel, sName) {
      return this.getView().setModel(oModel, sName);
    },

		/**
		 * Convenience method for getting the resource bundle.
		 * @public
		 * @returns {sap.ui.model.resource.ResourceModel} the resource model of the component
		 */
    getResourceBundle: function() {
      return this.getOwnerComponent().getModel("i18n").getResourceBundle();
    },
      
      /**
		 * Convenience method for navigate back.
		 * @public
		 */
    onNavBack: function () {
      var oHistory, sPreviousHash;
      oHistory = History.getInstance();
      sPreviousHash = oHistory.getPreviousHash();
      if (sPreviousHash !== undefined) {
        window.history.go(-1);
      } else {
        this.getRouter().navTo("projectList", {}, true /*no history*/);
      }
    }
  });
});