from odoo import models, fields, _


class DeliveryLineWizrd(models.TransientModel):
    _name = 'jsdemo.deliveryline.wizard'
    _description = 'jsdemo.deliveryline.wizard'

    date = fields.Date(string='Date',default=fields.Date.context_today)
    price = fields.Float('Price')
    trucker = fields.Char(string='Trucker')

    def add_line(self):
        self.env['jsdemo.deliveryline'].sudo().create({
            'date': self.date,
            'price': self.price,
            'trucker': self.trucker,
            'state': 'draft',
            'delivery_id': self.env.context.get('active_id'),
        })
        return {'type': 'ir.actions.act_window_close'}
