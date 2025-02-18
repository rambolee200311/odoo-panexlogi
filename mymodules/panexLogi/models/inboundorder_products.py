from odoo import api, fields, models, _
from odoo.exceptions import UserError


# 入库指令明细
class InboundOrderProducts(models.Model):
    _name = 'panexlogi.inbound.order.products'
    _description = 'panexlogi.inbound.order.products'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = 'billno'

    billno = fields.Char(string='BillNo', readonly=True)
    waybill_packlist_billno = fields.Many2one('panexlogi.waybill.packlist', string='packlist no')
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
    # already operated
    total_pallets = fields.Float(string='apPallets')  # , readonly=True, default=0)
    total_pcs = fields.Float(string='apPcs')  # , readonly=True, default=0)
    inboundorderproducts_scan_ids = fields.One2many('panexlogi.inbound.order.products.scan',
                                                    'inbound_order_products_id', string='Inbound Order Products Scan')

    color = fields.Integer()
    state = fields.Selection(
        selection=[
            ('new', 'New'),
            ('in-Operation', 'In-Operation'),
            ('completed', 'Completed'),
            ('cancel', 'Cancel'),
        ],
        default='new',
        string="State",
        tracking=True
    )

    inboundorderid = fields.Many2one('panexlogi.inbound.order', string='Inbound Order no')





    @api.model
    def create(self, values):
        """
        生成跟踪单号
        """
        times = fields.Date.today()
        values['billno'] = self.env['ir.sequence'].next_by_code('seq.inbound.order.products', times)
        values['state'] = 'new'
        return super(InboundOrderProducts, self).create(values)

    @api.onchange('waybill_packlist_billno')
    def _get_waybill_packlist(self):
        for r in self:
            if r.waybill_packlist_billno:
                r.batch = r.waybill_packlist_billno.batch
                r.interpono = r.waybill_packlist_billno.interpono
                r.product_id = r.waybill_packlist_billno.product_id
                r.powerperpc = r.waybill_packlist_billno.powerperpc
                r.pcs = r.waybill_packlist_billno.pcs
                r.pallets = r.waybill_packlist_billno.pallets
                r.totalvo = r.waybill_packlist_billno.totalvo
                r.cntrno = r.waybill_packlist_billno.cntrno
                r.sealno = r.waybill_packlist_billno.sealno


class InboundOrderProductsScan(models.Model):
    _name = 'panexlogi.inbound.order.products.scan'
    _description = 'panexlogi.inbound.order.products.scan'

    date = fields.Datetime(string='Date', default=fields.Datetime.now)
    warehouse_id = fields.Many2one(comodel_name='stock.warehouse', string='Warehouse')  # 仓库
    location_id = fields.Many2one(comodel_name='stock.location', string='Location')  # 库位
    pda_id = fields.Char(string='PDA ID')  # pda id for index
    product_id = fields.Many2one('product.product')  # 产品
    batch = fields.Char(string='Batch')  # 批号
    pcs = fields.Float(string='Pcs')  # 件数
    pallets = fields.Float(string='Pallets')  # 托数
    cntrno = fields.Char(string='Container No')  # 集装箱号
    palletdno = fields.Char(string='Pallet No')  # 托盘号
    sncode = fields.Char(string='SN Code')  # 序列号

    inbound_order_products_id = fields.Many2one('panexlogi.inbound.order.products', string='Inbound Order Products')
    #oder_billno = fields.Many2one('panexlogi.inbound.order.products', string='order product no')
    # 20241212
    be_del = fields.Boolean(string='Be Delete', default=False)
    ori_pda_id = fields.Char(string='Original PDA ID',default='')


    # constrains for pda_id
    @api.constrains('pda_id', 'inbound_order_products_id')
    def _check_pda_id(self):
        for r in self:
            domain = [
                ('pda_id', '=', r.pda_id),
                ('inbound_order_products_id', '=', r.inbound_order_products_id.id),
                ('id', '!=', r.id)
            ]
            existing_records = self.search(domain)
            if existing_records:
                raise UserError(_('PDA ID must be unique per Inbound Order Products'))

    # constrains for ori_pda_id
    def _check_ori_pda_id(self):
        for r in self:
            domain = [
                ('ori_pda_id', '!=', ''),
                ('ori_pda_id', '=', r.ori_pda_id),
                ('inbound_order_products_id', '=', r.inbound_order_products_id.id),
                ('id', '!=', r.id)
            ]
            existing_records = self.search(domain)
            if existing_records:
                raise UserError(_('Original PDA ID must be unique per Inbound Order Products'))
