from odoo import models, fields, api


class PanexDashboard(models.TransientModel):
    _name = 'panex.dashboard'
    _description = 'Panex Dashboard'

    waybill_count = fields.Integer(string="Waybill Count")
    transport_count = fields.Integer(string="Transport Count")
    delivery_count = fields.Integer(string="Delivery Count")
    ar_bill_count = fields.Integer(string="AR Bill Count")

    @api.model
    def default_get(self, fields):
        """Compute counts dynamically when the dashboard is opened"""
        res = super(PanexDashboard, self).default_get(fields)
        res.update({
            'waybill_count': self.env['panexlogi.waybill'].search_count([]),
            'transport_count': self.env['panexlogi.transport.order'].search_count([]),
            'delivery_count': self.env['panexlogi.delivery'].search_count([]),
            'ar_bill_count': self.env['panexlogi.ar.bill'].search_count([]),
        })
        return res

    def action_open_waybill(self):
        return self._get_action('panexlogi.waybill', 'Waybills')

    def action_open_transport(self):
        return self._get_action('panexlogi.transport.order', 'Transport Orders')

    def action_open_delivery(self):
        return self._get_action('panexlogi.delivery', 'Deliveries')

    def action_open_ar_bill(self):
        return self._get_action('panexlogi.ar.bill', 'AR Bills')

    def _get_action(self, model_name, name):
        """Generate common action structure"""
        return {
            'type': 'ir.actions.act_window',
            'name': name,
            'res_model': model_name,
            'view_mode': 'tree,form',
            'domain': [],
            'context': self.env.context,
        }