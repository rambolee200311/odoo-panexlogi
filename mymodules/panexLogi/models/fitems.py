from odoo import _, models, fields, api, exceptions
from odoo.exceptions import UserError


# 收入成本费用项目

class Fitems(models.Model):
    _name = 'panexlogi.fitems'
    _description = 'panexlogi.fitems'
    _rec_name = 'code'

    code = fields.Char(string='项目编码', required=True)
    name = fields.Char(string='项目名称', required=True)
    remark = fields.Text(string='Remark')
    remark1 = fields.Text(string='Remark1')
    booking_code = fields.Char(string='Booking Code(finance use only)')

    be_outcome = fields.Boolean("Outlay(费用支出)", default=True)
    be_income = fields.Boolean("Income（收入）", default=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirm'),
        ('cancel', 'Cancel'),
    ], string='Status', readonly=True, copy=False, index=True, default='draft')

    @api.constrains('code')
    def _check_code_id(self):
        for r in self:
            domain = [
                ('code', '=', r.code),
                ('id', '!=', r.id),
            ]
            existing_records = self.search(domain)
            if existing_records:
                raise UserError(_('Code must be unique per Finance item'))
