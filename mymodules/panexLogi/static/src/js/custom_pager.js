odoo.define('panexLogi.CustomPager', function (require) {
    "use strict";

    var ListView = require('web.ListView');
    ListView.include({
        render_pager: function($node) {
            this._super.apply(this, arguments);
            // 修改预定义选项
            this.pager_options.limits = [20, 50, 100, 200];
        }
    });
});