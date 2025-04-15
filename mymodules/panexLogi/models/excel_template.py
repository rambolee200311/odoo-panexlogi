from odoo import _, models, fields, api, exceptions
from odoo.exceptions import UserError, ValidationError


class ExcelTemplate(models.Model):
    _name = 'panexlogi.excel.template'
    _description = 'panexlogi.excel.template'

    type = fields.Selection(selection=[('inbound', 'Inbound'), ('delivery', 'Delivery')], string='Type', required=True)
    project = fields.Char(string='Project（项目）')
    remark = fields.Text(string='Remark（备注）')
    template_file = fields.Binary(string='Template File')
    template_file_name = fields.Char(string='Template File Name')

    # check if the combination of type and project is unique
    @api.constrains('type', 'project')
    def _check_type_and_project(self):
        for record in self:
            domain = [('type', '=', record.type), ('project', '=', record.project), ('id', '!=', record.id)]
            existing_records = self.search(domain)
            if existing_records:
                raise ValidationError(_('The combination of type and project must be unique.'))
