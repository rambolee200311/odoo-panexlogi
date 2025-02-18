from odoo import models, fields, api, _


# 入库操作明细
class InboundOperateProducts(models.Model):
    _name = 'panexlogi.inbound.operate.products'
    _description = 'panexlogi.inbound.operate.products'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = 'billno'

    billno = fields.Char(string='BillNo', readonly=True)
    oder_billno = fields.Many2one('panexlogi.inbound.order.products', string='order product no')
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')  # 仓库
    location_id = fields.Many2one('stock.location', string='Location')  # 库位号
    batch = fields.Char(string='Batch')  # 批号
    interpono = fields.Char(string='Inter-Company PO Number')
    product_id = fields.Many2one('product.product')
    powerperpc = fields.Integer(string='Power Per Piece')
    pcs = fields.Float(string='Pcs')
    pallets = fields.Float(string='Pallets')
    totalvo = fields.Float(string='Total Volume')
    cntrno = fields.Char(string='Container No')
    sealno = fields.Char(string='Seal Number')
    palletdno = fields.Char(string='Container No')  # 托盘号
    sncode = fields.Char(string='SN Code')  # SN码
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

    inboundoperateid = fields.Many2one('panexlogi.inbound.operate', string='Inbound Operate no')

    @api.model
    def create(self, values):
        """
        生成跟踪单号
        """
        times = fields.Date.today()
        values['billno'] = self.env['ir.sequence'].next_by_code('seq.inbound.operate.products', times)
        values['state'] = 'new'
        return super(InboundOperateProducts, self).create(values)
