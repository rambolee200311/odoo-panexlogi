from odoo import models, fields, api


class DemoStockPicking(models.Model):
    _name = 'jsdemo.demostockpicking'
    _description = 'jsdemo.demostockpicking'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = 'billno'

    billno = fields.Char(string='Bill No', readonly=True)
    barcode = fields.Char(string='Barcode')
    prouduct_id = fields.Many2one('product.product', string='Product ID')
    qty = fields.Float(string='Quantity', default=0)

    @api.model
    def create(self, values):
        """
        生成跟踪单号
        """
        times = fields.Date.today()
        values['billno'] = self.env['ir.sequence'].next_by_code('seq.demotodo', times)
        res = super(DemoStockPicking, self).create(values)

        return res