from odoo import models, fields


class DeliveryLine(models.Model):
    _name = 'jsdemo.deliveryline'
    _description = 'jsdemo.deliveryline'

    date = fields.Date(string='Date',default=fields.Date.context_today)
    price = fields.Float('Price')
    trucker = fields.Char(string='Trucker')
    state = fields.Char(string='State')
    delivery_id = fields.Many2one('jsdemo.delivery', string='Delivery', required=True)

    def btn_approve(self):
        self.write({'state': 'approve'})
        return {}

    def btn_decline(self):
        self.write({'state': 'decline'})
        return {}



