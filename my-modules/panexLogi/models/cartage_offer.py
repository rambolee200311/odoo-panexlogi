from datetime import datetime, timedelta
import pytz

from odoo import _, models, fields, api, exceptions
from odoo.exceptions import UserError, ValidationError

# 卡车运单报价
class CartageOffer(models.Model):
    _name = "panexlogi.cartage.offer"
    _description = "Cartage Offer Model"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = "billno"

    billno = fields.Char(string='Offer Code', readonly=True)
    costprice = fields.Float(string='Price of EUR', required=True, tracking=True)
    truckco = fields.Many2one('res.partner', string='Truck Co（卡车公司）', domain=[('truck', '=', 'True')])
    driverinfo = fields.Text(string='Driver Info（司机信息）')
    ddate = fields.Date(string='Date of Departure(出发日期)')
    adate = fields.Date(string='Date of Arrival(到达日期)')
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
            ('new', 'New'),
            ('accepted', 'Accepted'),
            ('refused', 'Refused')
        ],
        default='new',
        string="Offer Status"
    )

    @api.depends('cartagebillno')
    def _computer_order(self):
        for rec in self:
            rec.refno = self.cartagebillno.refno
            rec.sender = self.cartagebillno.sender.sender_name
            rec.sender_tel = self.cartagebillno.sender_tel
            rec.sender_address = self.cartagebillno.sender_address
            rec.consignee = self.cartagebillno.consignee.sender_name
            rec.consignee_tel = self.cartagebillno.consignee_tel
            rec.consignee_address = self.cartagebillno.consignee_address

    @api.model
    def create(self, values):
        """
        生成报价单号
        """
        times = fields.Date.today()
        values['billno'] = self.env['ir.sequence'].next_by_code('seq.cartage.offer', times)
        return super(CartageOffer, self).create(values)

    _sql_constraints = {(
        'check_expected_offer_price', 'CHECK(costprice >= 0)',
        'The offered price cannot be less than 0!!'
    )}

    def action_offer_accept(self):
        total_offers = self.cartagebillno.cartageoffer_ids
        for rec in self:
            if any(offer.status == "accepted" for offer in total_offers):
                raise UserError("Two offers cannot  be accepted at the same time!")
            rec.status = 'accepted'
            rec.cartagebillno.costprice = rec.costprice
            rec.cartagebillno.truckco = rec.truckco
            rec.cartagebillno.driverinfo=rec.driverinfo
            rec.cartagebillno.state = 'offer_accepted'

    def action_offer_refuse(self):
        for rec in self:
            rec.status = 'refused'
            # rec.cartagebillno.costprice = 0
            # rec.cartagebillno.truckco = ''
            # rec.cartagebillno.state = 'offer_received'

    def action_offer_renew(self):
        for rec in self:
            rec.status = 'new'
            # rec.cartagebillno.costprice = 0
            # rec.cartagebillno.truckco = ''
            # rec.cartagebillno.state = 'offer_received'