from odoo import _, models, fields, api
from datetime import timedelta

from odoo.exceptions import UserError


# 货柜明细

class WaybillDetails(models.Model):
    _name = 'panexlogi.waybill.details'
    _description = 'panexlogi.waybill.details'
    _inherit = ["mail.thread", "mail.activity.mixin"]

    cntrno = fields.Char(string='Container No')
    cntrnum = fields.Integer(string='Contrainer Num', default=1)
    pallets = fields.Float(string='Pallets',default=26)
    note = fields.Text(string='Note')

    waybill_billno = fields.Many2one('panexlogi.waybill')

    color = fields.Integer()
    state = fields.Selection(
        selection=[
            ('new', 'New'),
            ('confirm', 'Confirm'),
            ('cancel', 'Cancel'),
        ],
        default='new',
        string="State",
        tracking=True
    )
