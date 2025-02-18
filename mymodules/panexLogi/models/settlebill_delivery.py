from odoo import _, models, fields, api, exceptions
from odoo.exceptions import UserError


# 出库配送
class SettleBillDelivery(models.Model):
    _name = 'panexlogi.finance.settlebill.delivery'
    _description = 'panexlogi.finance.settlebill.delivery'

    cntrno = fields.Char(string='Container No.')
    palletqty = fields.Integer(string='Pallets ordered', default=0)
    orderno = fields.Char(string='Order number')
    truckprice = fields.Float(string='Trucking Cost', default=0)
    deliveryaddress= fields.Text(string='Delivery address', default=0)
    date = fields.Date(string='Outbound Date')
    extracost = fields.Float(string='Extra Cost', default=0)
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
        return super(SettleBillDelivery, self).unlink()



    @api.depends('extracost',
                 'truckprice')
    def _compute_amount(self):
        for rec in self:
            rec.amount = 0
            rec.amount = (rec.extracost
                          + rec.truckprice)
