from odoo import api, fields, models, _
from odoo.exceptions import UserError


# 入库指令明细
class OutboundOrderProducts(models.Model):
    _name = 'panexlogi.outbound.order.products'
    _description = 'panexlogi.outbound.order.products'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = 'billno'

    billno = fields.Char(string='BillNo', readonly=True)
    batch = fields.Char(string='Batch') #批号
    product_id = fields.Many2one('product.product')
    pcs = fields.Float(string='Pcs')
    pallets = fields.Float(string='Pallets')
    cntrno = fields.Char(string='Container No')
    palletdno=fields.Char(string='Container No') #托盘号

    color = fields.Integer()
    state = fields.Selection(
        selection=[
            ('new', 'New'),
            ('confirm', 'Confirm'),
            ('cancel', 'Cancel'),
        ],
        default='new',
        string="State",
        tracking=True
    )

    outboundorderid = fields.Many2one('panexlogi.outbound.order', string='Outbound Order no')

    @api.model
    def create(self, values):
        """
        生成跟踪单号
        """
        times = fields.Date.today()
        values['billno'] = self.env['ir.sequence'].next_by_code('seq.outbound.order.products', times)
        values['state'] = 'new'
        return super(OutboundOrderProducts, self).create(values)
