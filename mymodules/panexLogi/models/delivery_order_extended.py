from odoo import _, models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class TransportOrderDetailExtended(models.Model):
    _inherit = 'panexlogi.delivery.order'
    _description = 'panexlogi.delivery.order.extended'


    # outbound
    outbound_date = fields.Datetime(string='Outbound Date')
    outbound_remark = fields.Text('Outbound Remark')
    outbound_attach_file = fields.One2many(
        'ir.attachment', 'res_id',
        string='Attachments',
        domain=[('res_model', '=', 'panexlogi.delivery.order')],
        help='Upload multiple files related to this record'
    )

    # receive
    receive_date = fields.Datetime(string='Receive Date')
    receive_remark = fields.Text('Receive Remark')
    cmr_receive_file = fields.Binary(string='CMR Receive File')
    cmr_receive_filename = fields.Char(string='CMR Receive File Name')
    receive_attach_file = fields.One2many(
        'ir.attachment', 'res_id',
        string='Attachments',
        domain=[('res_model', '=', 'panexlogi.delivery.order')],
        help='Upload multiple files related to this record'
    )

    # return



