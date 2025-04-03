from odoo import _, models, fields, api
from datetime import timedelta

from odoo.exceptions import UserError


# 货柜明细

class WaybillDetails(models.Model):
    _name = 'panexlogi.waybill.details'
    _description = 'panexlogi.waybill.details'
    _inherit = ["mail.thread", "mail.activity.mixin"]

    uncode = fields.Char('UN CODE')
    cntrno = fields.Char(string='Container No')
    cntrnum = fields.Integer(string='Contrainer Num', default=1)
    pallets = fields.Float(string='Pallets', default=26)
    note = fields.Text(string='Note')
    pcs = fields.Float(string='Pcs', default=1)

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
    #check if waybill_billno.adr=ture then uncode is required
    @api.constrains('uncode')
    def _check_uncode(self):
        for rec in self:
            if rec.waybill_billno.adr and not rec.uncode:
                raise UserError(_("UN Code is required!"))