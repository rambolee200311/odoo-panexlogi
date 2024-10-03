from odoo import _, models, fields, api, exceptions


# 收入成本费用项目

class Fitems(models.Model):
    _name = 'panexlogi.fitems'
    _description = 'panexlogi.fitems'
    _rec_name = 'code'

    code = fields.Char(string='项目编码', required=True)
    name = fields.Char(string='项目名称', required=True)
    remark = fields.Text(string='Remark')

    be_outcome = fields.Boolean("Outlay(费用支出)", default=True)
    be_income = fields.Boolean("Income（收入）", default=True)
