sap.ui.define([
], function() {
  "use strict";

  return {
    formatJSONDateToString: function(oJSONDate){
      if(oJSONDate){
        return oJSONDate.toLocaleDateString();
      }
      return "";
    },
      
    formatIssuePriority: function(iPriority) {
      return  iPriority === 1 ? "High" : "None";
    }   
  };
});