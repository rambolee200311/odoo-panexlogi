from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ClearanceType(models.Model):
    _name = 'panexlogi.clearance.type'
    _description = 'panexlogi.clearance.type'
    _rec_name = 'name'

    code = fields.Char(string='Code', required=True)
    name = fields.Char(string='Name', required=True)
    description = fields.Text(string='Description')

    @api.constrains('code')
    def _check_code(self):
        for record in self:
            # Check if the code is unique
            if self.search_count([('code', '=', record.code), ('id', '!=', record.id)]) > 0:
                raise ValidationError(f'The code {record.code} must be unique!')
