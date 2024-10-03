from odoo import _, models, fields, api, exceptions
from odoo.exceptions import UserError


# 出库操作
class SettleBillOutbound(models.Model):
    _name = 'panexlogi.finance.settlebill.outbound'
    _description = 'panexlogi.finance.settlebill.outbound'

    date = fields.Date(string='Outbound Date')
    palletqty = fields.Integer(string='Pallet Amount', default=0)
    unitprice = fields.Float(string='Unitprice P/P', default=0)
    outboundcosts = fields.Float(string='Outbound unloading costs P/B', compute='_compute_outboundcost', store=True)
    blno = fields.Char(string='BL number')
    cntrno = fields.Char(string='Container No.')
    truckprice = fields.Float(string='Trucking Price P\C', default=0)
    waittime = fields.Char(string='Waiting time')
    termianlsurcharge = fields.Float(string='Terminal surcharge (RWG 18.15 per appointment)')
    amount = fields.Float(string='Amount', compute='_compute_amount', default=0, store=True)
    note = fields.Text(string='Note')

    settlebill_billno = fields.Many2one('panexlogi.finance.settlebill')

    """
    confirm
    received
    状态下不可删除
    ↓↓↓
    """

    def unlink(self):
        if self.settlebill_billno.state in ['confirm', 'received']:
            raise UserError('You cannot delete a record with state: %s' % self.settlebill_billno.state)
        return super(SettleBillOutbound, self).unlink()

    @api.depends('palletqty',
                 'unitprice')
    def _compute_outboundcost(self):
        for rec in self:
            rec.outboundcosts = 0
            rec.outboundcosts = (rec.palletqty
                                * rec.unitprice)

    @api.depends('outboundcosts',
                 'truckprice',
                 'termianlsurcharge')
    def _compute_amount(self):
        for rec in self:
            rec.amount = 0
            rec.amount = (rec.outboundcosts
                          + rec.truckprice
                          + rec.termianlsurcharge)
