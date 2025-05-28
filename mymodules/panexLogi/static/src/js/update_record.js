odoo.define('panexLogi.update_record_action', ['web.ActionManager'], function (require) {
    "use strict";

    const ActionManager = require('web.ActionManager');

    ActionManager.include({
        /**
         * Override the _handleAction method to intercept update_record actions
         * @param {Object} action - The action object
         * @param {Object} options - Additional options
         * @returns {Promise} Resolved promise when action is handled
         */
        _handleAction: function (action, options) {
            if (action.tag === 'update_record') {
                // Retrieve the active record ID from action parameters
                const activeId = action.params.active_id;

                // Trigger switching to form view for the selected record
                this.trigger_up('switch_view', {
                    view_type: 'form',
                    res_id: activeId,
                });

                // Resolve the promise as the action is handled
                return Promise.resolve();
            }
            // For other actions, use the default behavior
            return this._super(action, options);
        },
    });
});