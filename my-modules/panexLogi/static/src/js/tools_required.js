/** @odoo-module **/
// 给字段添加必输的红色星号 *
import { FormLabel } from '@web/views/form/form_label';
import { patch } from "@web/core/utils/patch";


patch(FormLabel.prototype, 'static/src/js/tools_required.js', {

    get hasRequired() {
        return this.props.fieldInfo.modifiers.required
    }
});



