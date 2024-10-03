# 卡车运单跟踪
from odoo import models, fields, api


class CartageTrail(models.Model):
    _name = "panexlogi.cartage.trail"
    _description = "Cartage Trail Model"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = "billno"

    billno = fields.Char(string='Offer Code', readonly=True)
    cmrfile = fields.Binary(string='CMR（原件）')
    cmrfilename = fields.Char(string='File name')
    truckco = fields.Many2one('res.partner', string='Truck Co（卡车公司）', domain=[('truck', '=', 'True')])
    driver = fields.Char(string='Driver Info')
    ddate = fields.Date(string='Date of Departure(出发日期)', tracking=True)
    adate = fields.Date(string='Date of Arrival(到达日期)', tracking=True)
    remark = fields.Char(string='Remark')
    cartagebillno = fields.Many2one('panexlogi.cartage')
    refno = fields.Char(string='REF NO', compute='_computer_order')
    sender = fields.Char(string='Sender Name', compute='_computer_order')
    sender_tel = fields.Char(string='Phone of Sender', compute='_computer_order')
    sender_address = fields.Char(string='Address of Sender', compute='_computer_order')
    consignee = fields.Char(string='Consignee Name', compute='_computer_order')
    consignee_tel = fields.Char(string='Phone of Consignee', compute='_computer_order')
    consignee_address = fields.Char(string='Address of Consignee', compute='_computer_order')

    status = fields.Selection(
        selection=[
            ('sent', 'Sent'),
            ('received', 'Received')
        ],
        string="Trail Status", tracking=True
    )

    @api.depends('cartagebillno')
    def _computer_order(self):
        for rec in self:
            rec.refno = self.cartagebillno.refno
            rec.sender = self.cartagebillno.sender
            rec.sender_tel = self.cartagebillno.sender_tel
            rec.sender_address = self.cartagebillno.sender_address
            rec.consignee = self.cartagebillno.consignee
            rec.consignee_tel = self.cartagebillno.consignee_tel
            rec.consignee_address = self.cartagebillno.consignee_address

    @api.model
    def create(self, values):
        """
        生成跟踪单号
        """
        times = fields.Date.today()
        values['billno'] = self.env['ir.sequence'].next_by_code('seq.cartage.trail', times)
        return super(CartageTrail, self).create(values)

    def action_trail_sent(self):
        for rec in self:
            rec.status = 'sent'
            rec.cartagebillno.state = 'sent'

    def action_trail_received(self):
        for rec in self:
            rec.status = 'received'
            rec.cartagebillno.state = 'received'
