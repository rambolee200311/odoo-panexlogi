from datetime import timedelta

from odoo import _, models, fields, api
from odoo.exceptions import UserError
'''
    Transport Contract
'''


class TransportContract(models.Model):
    _name = 'panexlogi.transport.contract'
    _description = 'panexlogi.transport.contract'
    _inherit = ["mail.thread", "mail.activity.mixin"]

    truckco = fields.Many2one('res.partner', string='Truck Co（卡车公司）', domain=[('truck', '=', 'True')])
    truckco_code = fields.Char(string='Truck Co Code', related='truckco.panex_code', readonly=True)
    begin_date = fields.Date(string='Begin Date', default=fields.Date.today)
    end_date = fields.Date(string='End Date')
    remark = fields.Text(string='Remark')
    transportcontractwarehaouseids = fields.One2many('panexlogi.transport.contract.warehaouse', 'transportcontractid',
                                                     string='To Warehouse')
    transportcontractfixedchargesids = fields.One2many('panexlogi.transport.contract.fixedcharges',
                                                       'transportcontractid', string='Additional Charges')

    uwt = fields.Float(string='UWT drop off')
    multistop = fields.Float(string='Multistop')
    multistoppkm = fields.Float(string='Multistop per km')
    adminfee = fields.Float(string='Admin Fee per container')
    waithours = fields.Integer(string='Waiting Hours Free')
    extrahours = fields.Float(string='Extra Hours(per hour/quarter)')
    adr = fields.Float(string='ADR')
    transportcontractotherdocs_ids = fields.One2many('panexlogi.transport.contract.otherdocs', 'billno')

    state = fields.Selection(
            selection=[
                ('new', 'New'),
                ('confirm', 'Confirm'),
                ('cancel', 'Cancel'),
            ],
            default='new',
            string="Status",
            tracking=True)

    def action_confirm_order(self):
        for rec in self:
            if rec.state != 'new':
                raise UserError(_("You only can confirm New Contract"))
            else:
                rec.state = 'confirm'
                return True

    def action_unconfirm_order(self):
        for rec in self:
            if rec.state != 'confirm':
                raise UserError(_("You only can unconfirm Confirmed Contract"))
            else:
                rec.state = 'new'
                return True

    def action_cancel_order(self):
        for rec in self:
            if rec.state != 'new':
                raise UserError(_("You only can cancel New Contract"))
            else:
                rec.state = 'cancel'
                return True


'''
    to warehouse charge
'''


class TransportContractWarhouse(models.Model):
    _name = 'panexlogi.transport.contract.warehaouse'
    _description = 'panexlogi.transport.contract.warehaouse'

    warehouse = fields.Many2one('stock.warehouse', string='Warehouse')
    warehouse_code = fields.Char(string='Warehouse Code', related='warehouse.code', readonly=True)
    charge = fields.Float(string='Charge')
    bevat = fields.Boolean(string='With Vat')
    vatrate = fields.Float(string='Vat Rate')
    remark = fields.Text(string='Remark')
    transportcontractid = fields.Many2one('panexlogi.transport.contract', string='Transport Contract')


class TransportContractFixedCharges(models.Model):
    _name = 'panexlogi.transport.contract.fixedcharges'
    _description = ('panexlogi.transport.contract.fixedcharges')

    terminal = fields.Many2one('panexlogi.terminal', string='Terminal')
    terminal_code = fields.Char(string='Terminal Code', related='terminal.terminal_code', readonly=True)
    charge = fields.Float(string='Charge')
    bevat = fields.Boolean(string='With Vat')
    vatrate = fields.Float(string='Vat Rate')
    remark = fields.Text(string='Remark')
    transportcontractid = fields.Many2one('panexlogi.transport.contract', string='Transport Contract')

# 其他附件
class TransportContractOtherDocs(models.Model):
    _name = 'panexlogi.transport.contract.otherdocs'
    _description = 'panexlogi.transport.contract.otherdocs'

    description = fields.Text(string='Description')
    file = fields.Binary(string='File')
    filename = fields.Char(string='File name')
    billno = fields.Many2one('panexlogi.transport.contract', string='Transport Contract BillNo')
