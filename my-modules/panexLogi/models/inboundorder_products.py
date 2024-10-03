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
    batch = fields.Char(string='Batch') #批号
    interpono = fields.Char(string='Inter-Company PO Number')
    product_id = fields.Many2one('product.product')
    powerperpc = fields.Integer(string='Power Per Piece')
    pcs = fields.Float(string='Pcs')
    pallets = fields.Float(string='Pallets')
    totalvo = fields.Float(string='Total Volume')
    cntrno = fields.Char(string='Container No')
    sealno = fields.Char(string='Seal Number')
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
