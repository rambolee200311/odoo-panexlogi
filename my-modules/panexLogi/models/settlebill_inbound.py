from odoo import _, models, fields, api, exceptions
from odoo.exceptions import UserError


# 入库操作
class SettleBillInbound(models.Model):
    _name = 'panexlogi.finance.settlebill.inbound'
    _description = 'panexlogi.finance.settlebill.inbound'

    date = fields.Date(string='Inbound Date')
    palletqty = fields.Integer(string='Pallet Amount', default=0)
    unitprice = fields.Float(string='Unitprice P/P', default=0)
    inboundcosts = fields.Float(string='Inbound unloading costs P/B', compute='_compute_inboundcost', store=True)
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
        return super(SettleBillInbound, self).unlink()

    @api.depends('palletqty',
                 'unitprice')
    def _compute_inboundcost(self):
        for rec in self:
            rec.inboundcosts = 0
            rec.inboundcosts = (rec.palletqty
                                * rec.unitprice)

    @api.depends('inboundcosts',
                 'truckprice',
                 'termianlsurcharge')
    def _compute_amount(self):
        for rec in self:
            rec.amount = 0
            rec.amount = (rec.inboundcosts
                          + rec.truckprice
                          + rec.termianlsurcharge)
