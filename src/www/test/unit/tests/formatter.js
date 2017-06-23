sap.ui.require([
  "com/sap/cloudscame/CATDashboard/model/formatter",
  "sap/ui/thirdparty/sinon-qunit"
],
    function (formatter) {
      "use strict";

      QUnit.test("Should return a String date with local format", function (assert) {
        // System under test
        this.oDate = new Date(1476496800000);
        this.sDate = formatter.formatJSONDateToString(this.oDate);

        // Assert
        assert.strictEqual(this.sDate, this.oDate.toLocaleDateString(), "The string is correct");
      });
    
      QUnit.test("Should return a empty String, because the object is null", function (assert) {
        // System under test
        this.sDate = formatter.formatJSONDateToString(null);

        // Assert
        assert.strictEqual(this.sDate, "", "The string is correct");
      });
    
      QUnit.test("Should return high priority for Show Stopper issue", function (assert) {
        // System under test
        this.sPriority = formatter.formatIssuePriority(1);

        // Assert
        assert.strictEqual(this.sPriority, "High", "The string is correct");
      });
    
      QUnit.test("Should return None priority for Nice to Have issue", function (assert) {
        // System under test
        this.sPriority = formatter.formatIssuePriority(0);

        // Assert
        assert.strictEqual(this.sPriority, "None", "The string is correct");
      });
    });