from odoo import _, models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class TransportOrderDetailExtended(models.Model):
    _inherit = 'panexlogi.transport.order.detail'
    _description = 'panexlogi.transport.order.detail.extended'

    billno = fields.Char(string='BillNo', related='transportorderid.billno', readonly=True)
    project = fields.Many2one('panexlogi.project', string='Project', related='transportorderid.project', readonly=True)
    order_state = fields.Selection(string='Order Status', related='transportorderid.state', readonly=True)
    waybill_billno = fields.Many2one('panexlogi.waybill', related='transportorderid.waybill_billno',
                                     string='Waybill No', readonly=True)
    waybillno = fields.Char(string='Waybill No', related='waybill_billno.waybillno', readonly=True)
    cmr_signed = fields.Binary(string='CMR Signed')
    cmr_signed_name = fields.Char(string='CMR Signed Name')
    arrived_remark = fields.Text(string='Arrive Remark')
    model_type = fields.Char(string='Model Type')
    weight_kg = fields.Float(string='Weight (kg)')
    total_pcs = fields.Float(string='Total Pieces')

    attachment_ids = fields.One2many(
        'ir.attachment', 'res_id',
        string='Attachments',
        domain=[('res_model', '=', 'panexlogi.transport.order.detail')],
        help='Upload multiple files related to this record'
    )

    # @api.model
    def set_arrived(self):
        self.ensure_one()  # Ensure single record operation
        if self.state == 'arrived':
            raise UserError(_('This order had been set as arrived.'))
        try:
            return {
                'name': 'Set Arrived',
                'type': 'ir.actions.act_window',
                'res_model': 'panexlogi.transport.order.set.arrived.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_arrived_date': fields.Date.today(),
                    'default_arrived_remark': self.arrived_remark,
                    'default_cmr_signed': self.cmr_signed,
                    'default_cmr_signed_name': self.cmr_signed_name,
                    'active_id': self.id,  # Now correctly references current record
                },
            }
        except Exception as e:
            raise UserError(_('Error: %s') % str(e))


class TransportOrderSetArrivedWizard(models.TransientModel):
    _name = 'panexlogi.transport.order.set.arrived.wizard'
    _description = 'Set Arrived Wizard'
    _inherit = ["mail.thread", "mail.activity.mixin"]

    arrived_date = fields.Date(string='Arrived Date', default=fields.Date.today, required=True)
    arrived_remark = fields.Text(string='Arrive Remark')
    cmr_signed = fields.Binary(string='CMR Signed', required=True)
    cmr_signed_name = fields.Char(string='CMR Signed Name')
    """
    attachment_ids = fields.One2many(
        'ir.attachment', 'res_id',
        string='Attachments',
        # domain=[('res_model', '=', 'panexlogi.transport.order.set.arrived.wizard')],
        help='Upload multiple files related to this record'
    )
    """
    attachment_ids = fields.Many2many(
        'ir.attachment',
        string='Attachments',
        help="Files uploaded in the wizard",
    )

    def apply_changes(self):
        try:
            active_id = self.env.context.get('active_id')
            if active_id:
                record = self.env['panexlogi.transport.order.detail'].browse(active_id)
                # Ensure attachments are linked to the wizard
                self.attachment_ids.write({'res_model': self._name, 'res_id': self.id})
                _logger.info("Copying attachments from wizard: %s", self.attachment_ids)
                # Copy attachments and link to target record
                if self.attachment_ids:
                    for attachment in self.attachment_ids:
                        _logger.info("正在复制附件: %s", attachment.name)
                        # Explicitly set all required fields
                        new_attachment = attachment.copy({
                            'res_model': 'panexlogi.transport.order.detail',  # Target model
                            'res_id': record.id,  # Target record ID
                            'res_field': False,  # 清除字段绑定（避免与 cmr_signed 冲突）
                            'type': 'binary',  # 明确文件类型
                            'public': False,  # 设为私有附件
                            'name': attachment.name,  # Copy filename
                            'datas': attachment.datas,  # Copy file data
                        })
                        _logger.info("New attachment ID: %s | Model: %s | Res ID: %s",
                                     new_attachment.id,
                                     new_attachment.res_model,
                                     new_attachment.res_id)
                else:
                    _logger.warning("No attachments found in the wizard.")
                # Update other fields
                record.write({
                    'arrived_date': self.arrived_date,
                    'arrived_remark': self.arrived_remark,
                    'cmr_signed': self.cmr_signed,
                    'cmr_signed_name': self.cmr_signed_name,
                    'state': 'arrived',
                })
        except Exception as e:
            _logger.error("Error: %s", str(e))
            raise UserError(_('Error: %s') % str(e))
        return {'type': 'ir.actions.act_window_close'}
