from datetime import datetime, timedelta
import pytz

from odoo import _, models, fields, api, exceptions
from odoo.exceptions import UserError, ValidationError


# 卡车运单
class Cartage(models.Model):
    _name = 'panexlogi.cartage'
    _description = 'panexlogi.cartage'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = 'billno'

    billno = fields.Char(string='BillNo', readonly=True)
    date = fields.Date(string='Date（预定日期）', required=True)

    # cargoReleaseLine = fields.Many2one('panexlogi.waybill.cargoreleaseline', string='CNTR NO')
    inouttype=fields.Selection([('in', 'INBOUND'),
         ('out', 'OUTBOUND'),
         ('other', 'OTHER'),],
        string='IN/OUT', default="out")
    cntrno = fields.Char(string='CNTR NO', compute='_compute_cntrno')
    waybillno = fields.Char(string='Waybill No（提单号））', compute='_compute_cntrno')
    project = fields.Char(string='Project（项目）', compute='_compute_cntrno')
    refno = fields.Char(string='REF NO', required=True)
    remark = fields.Text(string='Remark（备注）')

    sender = fields.Many2one('panexlogi.sender', string='Sender Name', required=True)
    sender_tel = fields.Char(string='Phone of Sender')
    sender_address = fields.Char(string='Address of Sender')

    consignee = fields.Many2one('panexlogi.sender', string='Consignee Name', required=True)
    consignee_tel = fields.Char(string='Phone of Consignee')
    consignee_address = fields.Char(string='Address of Consignee')

    costprice = fields.Float(string='Price of EUR')
    truckco = fields.Many2one('res.partner', string='Truck Co（卡车公司）', domain=[('truck', '=', 'True')])
    driverinfo=fields.Text(string='Driver Info（司机信息）')

    tag_ids = fields.Many2many("panexlogi.cartage.tag", string="Tags")
    cartageoffer_ids = fields.One2many('panexlogi.cartage.offer', 'cartagebillno')
    cartagetrail_ids = fields.One2many('panexlogi.cartage.trail', 'cartagebillno')

    state = fields.Selection(
        selection=[
            ('new', 'New'),
            ('offer_accepted', 'Offer Accepted'),
            ('sent', 'Sent'),
            ('received', 'Received'),
            ('cancel', 'Cancel')
        ],
        default='new',
        string="Status"
    )

    color = fields.Integer()

    # ('offer_received', 'Offer Recieved'),

    @api.model
    def create(self, values):
        """
        生成跟踪单号
        """
        times = fields.Date.today()
        values['billno'] = self.env['ir.sequence'].next_by_code('seq.cartage', times)
        return super(Cartage, self).create(values)

    @api.ondelete(at_uninstall=False)
    def _unlink_if_not_new_or_canceled(self):
        if any(rec.state != 'new' and rec.state != 'cancel' for rec in self):
            raise UserError("You can only delete new or cancelled Order!!")

    def action_send_order(self):
        for rec in self:
            if rec.state == 'cancel':
                raise UserError(_("You cannot send Cancelled Order"))
            else:
                rec.state = 'send'
                return True

    def action_receive_order(self):
        for rec in self:
            if rec.state == 'cancel':
                raise UserError(_("You cannot receive Cancelled Order"))
            else:
                rec.state = 'receive'
                return True

    def action_cancel_order(self):
        for rec in self:
            if rec.state == 'send':
                raise UserError(_("You cannot cancel Send order"))
            else:
                rec.state = 'cancel'
                return True

    def action_renew_order(self):
        for rec in self:
            rec.state = 'new'
            return True

    @api.onchange('refno')
    def _compute_cntrno(self):
        # if self.cntrno:
        #     if self.cntrno.cargoreleaseid.waybill_billno.billno:
        #         self.waybillno = self.cntrno.cargoreleaseid.waybill_billno.billno
        #     if self.cntrno.cargoreleaseid.waybill_billno.project:
        #         self.project = self.cntrno.cargoreleaseid.waybill_billno.project
        # else:
        #     self.waybillno = ''
        #     self.project = ''

        for rec in self:
            cargoReleaseLine_obj = self.env['panexlogi.waybill.cargoreleaseline']
            result_obj = cargoReleaseLine_obj.search([('cntrno', '=', rec.refno), ])
            if result_obj:
                rec.cntrno = result_obj.cntrno
                rec.waybillno = result_obj.cargoreleaseid.waybill_billno.billno
                rec.project = result_obj.cargoreleaseid.waybill_billno.project.project_name
            else:
                rec.cntrno = ''
                rec.waybillno = ''
                rec.project = ''

    @api.onchange('sender')
    def onchange_sender(self):
        if self.sender:
            if self.sender.tel:
                self.sender_tel = self.sender.tel
            if self.sender.address:
                self.sender_address = self.sender.address
        else:
            self.sender_tel = ''
            self.sender_address = ''

    @api.onchange('consignee')
    def onchange_consignee(self):
        if self.consignee:
            if self.consignee==self.sender:
                self.consignee_tel = ''
                self.consignee_address = ''
                raise UserError(_("Consignee cannot same as Sender"))
            else:
                if self.consignee.tel:
                    self.consignee_tel = self.consignee.tel
                if self.consignee.address:
                    self.consignee_address = self.consignee.address
        else:
            self.consignee_tel = ''
            self.consignee_address = ''
