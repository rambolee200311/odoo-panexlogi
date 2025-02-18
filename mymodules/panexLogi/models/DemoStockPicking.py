from odoo import _, models, fields, api
from datetime import timedelta
from datetime import datetime
from odoo.exceptions import UserError


# 到港通知

class DemoStockPicking(models.Model):
    _name = 'panexlogi.demostockpicking'
    _description = 'panexlogi.demostockpicking'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = 'billno'

    billno = fields.Char(string='Bill No', readonly=True)
    barcode = fields.Char(string='Barcode',required=True)
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

    # @api.onchange('barcode')
    def on_barcode_scanned(self,barcode):
        product_rec = self.env['product.product']
        if self.barcode:
            product = product_rec.search([('barcode', '=', self.barcode)])
            self.product_id = product.id
            self.qty += 1
