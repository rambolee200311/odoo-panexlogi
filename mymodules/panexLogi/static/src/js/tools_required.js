/** @odoo-module **/
import { FormLabel } from "@web/views/form/form_label";
import { patch } from "@web/core/utils/patch";

patch(FormLabel.prototype, {
    get className() {
        const originalClass = super.className || '';
        if (!this.props.field || !this.props.fieldInfo) {
            return originalClass;
        }
        // 深度检查字段必填状态
        const fieldName = this.props.field?.name;
        const fieldInfo = this.props.fieldInfo || {};
        const modifiers = fieldInfo.modifiers || {};
        const isModelRequired = this.props.field?.required;
        const isViewRequired = modifiers.required || modifiers.requiredness;
        return `${originalClass} ${isModelRequired || isViewRequired ? 'o_required_blue_label' : ''}`;

    }
});