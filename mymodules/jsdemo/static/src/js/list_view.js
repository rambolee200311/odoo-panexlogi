odoo.define('trucking.paste', ['@web/views/list/list_renderer', '@web/core/orm_service'], function(require) {
"use strict";

const { ListRenderer } = require('@web/views/list/list_renderer');
const { registry } = require('@web/core/registry');
const { useService } = require("@web/core/utils/hooks");

// Patch the ListRenderer
registry.category('list_renderers').add('trucking_paste', class extends ListRenderer {
    async _onPaste(event) {
        event.preventDefault();
        const orm = useService("orm");
        const data = event.clipboardData.getData('text/plain');
        const lines = data.split('\n').filter(line => line.trim() !== '');

        await orm.call(
            'jsdemo.trucking.line',
            'process_pasted_data',
            [lines, this.props.list.resId]
        );

        this.props.list.model.load();
    }
});
});