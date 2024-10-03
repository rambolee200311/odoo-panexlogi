from odoo import _, models, fields, api
from datetime import timedelta

from odoo.exceptions import UserError
# 关税

class WaybillCustomsDuties(models.Model):
    _name = 'panexlogi.waybill.customsduties'
    _description = 'panexlogi.waybill.customsduties'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = 'billno'

    billno = fields.Char(string='Commer Invoice No', readonly=True)
    invno = fields.Char(string='Invoice No（发票号）', required=True, tracking=True)
    date = fields.Date(string='Issue Date（发票日期）', required=True, tracking=True)
    desc = fields.Char(string='Description(关税名称)', tracking=True)
    eurtotal = fields.Float(string='Total_of_EUR', required=True, tracking=True)
    pdffile = fields.Binary(string='File（原件）', tracking=True)
    pdffilename = fields.Char(string='File name')
    waybill_billno = fields.Many2one('panexlogi.waybill', tracking=True)
    project = fields.Many2one('panexlogi.project', string='Project（项目）', compute='_get_waybill')
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

    @api.model
    def create(self, values):
        """
        生成跟踪单号
        """
        times = fields.Date.today()
        values['billno'] = self.env['ir.sequence'].next_by_code('seq.waybill.custduty', times)
        return super(WaybillCustomsDuties, self).create(values)

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