from odoo import _, models, fields, api, exceptions
from odoo.exceptions import UserError


# 进口换单
class SettleBillHandling(models.Model):
    _name = 'panexlogi.finance.settlebill.handling'
    _description = 'panexlogi.finance.settlebill.handling'

    shipco = fields.Char(string='Ship Comapany')
    receiveco = fields.Char(string='Receiving Comapany')
    invoicedetail = fields.Char(string='Invoice Detail')
    invoiceno = fields.Char(string='Invoice No')
    blno = fields.Char(string='BL number')
    amount = fields.Float(string='Amount', default=0)
    othercost = fields.Float(string='Other Cost', default=0)
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
        return super(SettleBillHandling, self).unlink()
