from odoo import _, models, fields, api
from datetime import timedelta

from odoo.exceptions import UserError


#  放货证明

class WaybllCargoRelease(models.Model):
    _name = 'panexlogi.waybill.cargorelease'
    _description = 'panexlogi.waybill.cargorelease'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = 'billno'

    billno = fields.Char(string='Commer Invoice No', readonly=True)
    waybill_billno = fields.Many2one('panexlogi.waybill', tracking=True)
    date = fields.Date(string='Date', required=True, tracking=True)
    pdffile = fields.Binary(string='File（原件）', tracking=True)
    pdffilename = fields.Char(string='File name')
    project = fields.Many2one('panexlogi.project', string='Project（项目）', compute='_get_waybill')
    color = fields.Integer()
    cargoreleaslineids = fields.One2many('panexlogi.waybill.cargoreleaseline', 'cargoreleaseid', ' Details')
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

    @api.model
    def create(self, values):
        """
        生成跟踪单号
        """
        times = fields.Date.today()
        values['billno'] = self.env['ir.sequence'].next_by_code('seq.waybill.cargorelease', times)
        return super(WaybllCargoRelease, self).create(values)

    @api.onchange('waybill_billno')
    def _get_waybill(self):
        for r in self:
            self.project = self.waybill_billno.project

    def action_confirm_order(self):
        for rec in self:
            if rec.state != 'new':
                raise UserError(_("You only can confirm New Order"))
            else:
                rec.state = 'confirm'
                return True

    def action_unconfirm_order(self):
        for rec in self:
            if rec.state != 'confirm':
                raise UserError(_("You only can unconfirm Confirmed Order"))
            else:
                rec.state = 'new'
                return True

    def action_cancel_order(self):
        for rec in self:
            if rec.state != 'new':
                raise UserError(_("You only can cancel New Order"))
            else:
                rec.state = 'cancel'
                return True


#  放货证明明细

class WaybllCargoReleaseline(models.Model):
    _name = 'panexlogi.waybill.cargoreleaseline'
    _description = 'panexlogi.waybill.cargoreleasline'
    _rec_name = 'billno'

    billno = fields.Char(string='Bill No', readonly=True)
    cntrno = fields.Char(string='CNTR NO', required=True)
    pincode = fields.Char(string='PIN CODE', required=True)
    returndepot = fields.Char(string='RETURN DEPOT')
    releaseexpire = fields.Date(string='RELEASE EXPIRE', required=True)
    releasedepot = fields.Char(string='RELEASE DEPOT')
    cargoreleaseid = fields.Many2one('panexlogi.waybill.cargorelease')
    remark = fields.Text(string='Remark')

    @api.model
    def create(self, values):
        """
        生成跟踪单号
        """
        times = fields.Date.today()
        values['billno'] = self.env['ir.sequence'].next_by_code('seq.waybill.cargoreleaseline', times)
        return super(WaybllCargoReleaseline, self).create(values)
