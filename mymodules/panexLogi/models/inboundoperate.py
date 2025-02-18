from odoo import api, fields, models, _
from odoo.exceptions import UserError


# 入库指令
class InboundOperate(models.Model):
    _name = 'panexlogi.inbound.operate'
    _description = 'panexlogi.inbound.operate'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = 'billno'

    billno = fields.Char(string='BillNo', readonly=True)
    order_billno = fields.Many2one(comodel_name='panexlogi.inbound.order', string='Order No')
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
    pda_id = fields.Text(string='Pad ID')

    inbound_operate_product_ids = fields.One2many('panexlogi.inbound.operate.products', 'inboundoperateid')

    @api.model
    def create(self, values):
        """
        生成跟踪单号
        """
        times = fields.Date.today()
        values['billno'] = self.env['ir.sequence'].next_by_code('seq.inbound.operate', times)
        values['state'] = 'new'
        return super(InboundOperate, self).create(values)

    @api.constrains('pda_id')
    def _check_pda_id(self):
        for r in self:
            domain = [
                ('pda_id', '=', r.pda_id),
                ('id', '!=', r.id)
            ]
            existing_records = self.search(domain)
            if existing_records:
                raise UserError(_('PDA ID must be unique per Inbound Order Operate'))
