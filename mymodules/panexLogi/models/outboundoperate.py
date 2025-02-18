from odoo import api, fields, models, _
from odoo.exceptions import UserError


# 入库指令
class OutboundOperate(models.Model):
    _name = 'panexlogi.outbound.operate'
    _description = 'panexlogi.outbound.operate'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = 'billno'

    billno = fields.Char(string='BillNo', readonly=True)
    order_billno = fields.Many2one(comodel_name='panexlogi.outbound.order', string='Order No')
    date = fields.Date(string='Date（单据日期）', required=True, tracking=True, default=fields.Date.today)
    warehouse = fields.Many2one(comodel_name='stock.warehouse', string='Warehouse')
    remark = fields.Text(string='Remark')
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

    outbound_operate_product_ids = fields.One2many('panexlogi.outbound.operate.products', 'outboundoperateid')

    @api.model
    def create(self, values):
        """
        生成跟踪单号
        """
        times = fields.Date.today()
        values['billno'] = self.env['ir.sequence'].next_by_code('seq.outbound.operate', times)
        values['state'] = 'new'
        return super(OutboundOperate, self).create(values)
