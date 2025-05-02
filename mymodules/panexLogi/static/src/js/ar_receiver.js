odoo.define('panexLogi.CustomListRenderer', function (require) {
    "use strict";
    var ListRenderer = require('web.ListRenderer');
    ListRenderer.include({
        _renderFooter: function () {
            return $(`
                <tfoot>
                    <tr><td colspan="10">Global Receive Total:</td><td>${this.state.global_receive_total}</td></tr>
                    <tr><td colspan="10">Global Cost Total:</td><td>${this.state.global_cost_total}</td></tr>
                </tfoot>
            `);
        }
    });
});