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

    def action_open_change_wizard(self):
        # 仅传递上下文，不返回动作
        return {
            'type': 'ir.actions.act_window',
            'name': 'Change Log',  # 确保标题一致
            'res_model': 'delivery.order.change.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_delivery_order_id': self.id,
            },
        }

    # return


class DeliveryOrderChangeLog(models.Model):
    _name = 'delivery.order.change.log'
    _description = 'Delivery Order Change Log'

    delivery_order_id = fields.Many2one(
        'panexlogi.delivery.order',
        string='Delivery Order',
        ondelete='cascade',
        required=True
    )
    extra_cost = fields.Float(string='Extra Cost')
    charge = fields.Float(string='Charge')
    reason = fields.Text(string='Reason')
    remark = fields.Text(string='Remark')
    change_time = fields.Datetime(string='Change Time', default=fields.Datetime.now)


class DeliveryOrderChangeWizard(models.TransientModel):
    _name = 'delivery.order.change.wizard'
    _description = 'Delivery Order Change Wizard'

    delivery_order_id = fields.Many2one('panexlogi.delivery.order', string='Delivery Order', required=True,
                                        readonly=True)
    extra_cost = fields.Float(string='Extra Cost (add)')
    charge = fields.Float(string='Charge (add)')
    reason = fields.Text(string='Reason')
    remark = fields.Text(string='Remark')

    def action_record_change(self):
        """Record the change and log it in a history model."""
        self.env['delivery.order.change.log'].create({
            'delivery_order_id': self.delivery_order_id.id,
            'extra_cost': self.extra_cost,
            'charge': self.charge,
            'reason': self.reason,
            'remark': self.remark,
            'change_time': fields.Datetime.now(),
        })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': 'Change recorded successfully!',
                'type': 'success',
                'sticky': False,
            }
        }, {
            'type': 'ir.actions.act_window_close'
        }
