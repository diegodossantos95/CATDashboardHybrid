sap.ui.define([
  "com/sap/cloudscame/CATDashboard/controller/BaseController",
  "com/sap/cloudscame/CATDashboard/model/utils"
], function (BaseController, utils) {
  "use strict";
  return BaseController.extend("com.sap.cloudscame.CATDashboard.controller.App", {
    onInit: function () {
      this.getView().addStyleClass(utils.getContentDensityClass());
    }
  });
});