sap.ui.define([
  'sap/ui/core/UIComponent',
  'com/sap/cloudscame/CATDashboard/model/models'
], function (UIComponent, models) {
  'use strict';
  return UIComponent.extend('com.sap.cloudscame.CATDashboard.Component', {
    metadata: {
      manifest: 'json'
    },
        /**
         * The component is initialized by UI5 automatically during the startup of the app and calls the init method once.
         * @public
         * @override
         */
    init: function () {
            //Call the base component's init function
      UIComponent.prototype.init.apply(this, arguments);
            
            //Initialize the router
      this.getRouter().initialize();

            // Set the device model
      this.setModel(models.getDeviceModel(), "Device");
    }
  });
});