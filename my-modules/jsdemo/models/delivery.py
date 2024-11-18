from odoo import models, fields, _


class Delivery(models.Model):
    _name = 'jsdemo.delivery'
    _description = 'jsdemo.delivery'

    date = fields.Date(string='Date', readonly=True, default=fields.Date.context_today)
    project = fields.Char(string='Project')
    remark = fields.Text('Remark')
    price = fields.Float('Price')
    trucker = fields.Char(string='Trucker')
    delivery_line_ids = fields.One2many('jsdemo.deliveryline', 'delivery_id', string='Delivery Lines')


    # 跳转wizard视图
    def add_line(self):
        return {
            'name': 'Add Quotation',
            'type': 'ir.actions.act_window',
            'res_model': 'jsdemo.deliveryline.wizard',
            'view_mode': 'form',
            'target': 'new',
        }

