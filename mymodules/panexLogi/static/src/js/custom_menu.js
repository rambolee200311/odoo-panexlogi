odoo.define('panexLogi.custom_menu', function (require) {
    "use strict";

    var WebClient = require('web.WebClient');

    WebClient.include({
        show_application: function () {
            this._super.apply(this, arguments);
            this._move_submenu_to_left();
        },
        _move_submenu_to_left: function () {
            var $submenu = $('.o_sub_menu');
            if ($submenu.length) {
                $submenu.addClass('left-navbar');
                $('body').append($submenu);
            }
        },
    });
});