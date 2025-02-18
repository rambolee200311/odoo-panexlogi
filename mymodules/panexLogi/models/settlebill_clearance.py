from odoo import _, models, fields, api, exceptions
from odoo.exceptions import UserError


# 进口清关
class SettleBillClearance(models.Model):
    _name = 'panexlogi.finance.settlebill.clearance'
    _description = 'panexlogi.finance.settlebill.clearance'

    declaration = fields.Char(string='Customs declaration')
    blno = fields.Char(string='BL number')
    vatintro = fields.Float(string='VAT intro', default=0)
    enitemno = fields.Integer(string='Entry Item number', default=0)
    exitemno = fields.Integer(string='Extra Item number', default=0)
    amount = fields.Float(string='Amount', default=0)
    note = fields.Text(string='Note')
    Remark = fields.Text(string='Remark')

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
        return super(SettleBillClearance, self).unlink()
