from odoo import models, fields, api


class TransportOrderDetailExtended(models.Model):
    #_name = 'panexlogi.transport.order.detail.extended'
    _inherit = 'panexlogi.transport.order.detail'
    _description = 'panexlogi.transport.order.detail.extended'

    billno = fields.Char(string='BillNo', related='transportorderid.billno', readonly=True)
    project = fields.Many2one('panexlogi.project', string='Project', related='transportorderid.project', readonly=True)
    order_state = fields.Selection(string='Order Status', related='transportorderid.state', readonly=True)
    waybill_billno = fields.Many2one('panexlogi.waybill', related='transportorderid.waybill_billno',string='Waybill No', readonly=True)
    waybillno = fields.Char(string='Waybill No', related='waybill_billno.waybillno', readonly=True)
    cmr_signed = fields.Binary(string='CMR Signed')
    cmr_signed_name = fields.Char(string='CMR Signed Name')
    arrived_remark = fields.Text(string='Arrive Remark')
    @api.model
    def set_arrived(self, vals):
        return {
            'name': 'Set Arrived',
            'type': 'ir.actions.act_window',
            'res_model': 'panexlogi.transport.order.set.arrived.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_arrived_date': fields.Date.today(),
                'default_arrived_remark': '',
                'default_cmr_signed': False,
                'default_cmr_signed_name': '',
                'active_id': self.id,
            },
        }
class TransportOrderSetArrivedWizard(models.TransientModel):
    _name = 'panexlogi.transport.order.set.arrived.wizard'
    _description = 'Set Arrived Wizard'

    arrived_date = fields.Date(string='Arrived Date', default=fields.Date.today, required=True)
    arrived_remark = fields.Text(string='Arrive Remark')
    cmr_signed = fields.Binary(string='CMR Signed', required=True)
    cmr_signed_name = fields.Char(string='CMR Signed Name')

    def apply_changes(self):
        active_id = self.env.context.get('active_id')
        if active_id:
            record = self.env['panexlogi.transport.order.detail'].browse(active_id)
            record.write({
                'arrived_date': self.arrived_date,
                'arrived_remark': self.arrived_remark,
                'cmr_signed': self.cmr_signed,
                'cmr_signed_name': self.cmr_signed_name,
                'state': 'arrived',
            })
        return {'type': 'ir.actions.act_window_close'}
