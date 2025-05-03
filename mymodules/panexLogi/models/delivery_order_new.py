from datetime import datetime, timedelta
import pytz

from odoo import _, models, fields, api, exceptions
from odoo.exceptions import UserError, ValidationError
import logging
import base64
from io import BytesIO
import openpyxl

_logger = logging.getLogger(__name__)


class DeliveryOrderNew(models.Model):
    _name = 'panexlogi.delivery.order.new'
    _description = 'panexlogi.delivery.order.new'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = 'billno'

    billno = fields.Char(string='BillNo', readonly=True)
    date = fields.Date(string='Date', default=fields.Date.today())
    project = fields.Many2one('panexlogi.project', string='Project（项目）', required=True)
    project_code = fields.Char(string='Project Code', related='project.project_code', readonly=True)
    truckco = fields.Many2one('res.partner', string='Truck Co（卡车公司）', required=True)
    truckco_code = fields.Char(string='Truck Co Code', related='truckco.panex_code', readonly=True)
    delivery_id = fields.Many2one('panexlogi.delivery', string='Delivery ID')
    trailer_type = fields.Many2one('panexlogi.trailertype', string='Type of trailer')
    state = fields.Selection([
        ('new', 'New'),
        ('confirm', 'Confirm'),
        ('cancel', 'Cancel')
    ], string='State', default='new', readonly=True, tracking=True)
    delivery_state = fields.Selection([
        ('none', 'None'),
        ('order', 'Order Placed'),
        ('transit', 'In Transit'),
        ('delivery', 'Delivered'),
        ('cancel', 'Cancel'),
        ('return', 'Return'),
        ('other', 'Other'),
        ('complete', 'Complete'),
    ], string='Delivery State', readonly=True, default='none')

    # outside_eu, import_file,export_file, transit_file
    outside_eu = fields.Boolean(string='Outside of EU')
    import_file = fields.Binary(string='Import File')
    import_filename = fields.Char(string='Import File Name')
    export_file = fields.Binary(string='Export File')
    export_filename = fields.Char(string='Export File Name')
    quote = fields.Float('Quote', default=0, tracking=True, readonly=True)
    additional_cost = fields.Float('Additional Cost', default=0, tracking=True, readonly=True)  # 额外费用
    extra_cost = fields.Float('Extra Cost', default=0, tracking=True, readonly=True)
    delivery_detail_cmr_ids = fields.Many2many(
        'panexlogi.delivery.detail.cmr',
        'delivery_detail_cmr_rel',
        'delivery_order_id',
        'cmr_detail_id',
        string='CMR Details'
    )

    delivery_detail_ids = fields.Many2many(
        'panexlogi.delivery.detail',
        'delivery_detail_rel',
        'delivery_order_id',
        'detail_id',
        string='Delivery Details'
    )

    @api.model
    def create(self, values):
        """
            生成订单号
        """
        times = fields.Date.today()
        values['billno'] = self.env['ir.sequence'].next_by_code('seq.delivery.order', times)
        delivery_request = super(DeliveryOrderNew, self).create(values)
        return delivery_request

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
                for line in rec.deliver_datail_cmr_ids:
                    line.delivery_order_new_id = False
                rec.state = 'cancel'
                # rec.delivery_id.state = 'confirm'
                return True

    # The method returns an action dictionary that opens the delivery.order.new.wizard in a form view


