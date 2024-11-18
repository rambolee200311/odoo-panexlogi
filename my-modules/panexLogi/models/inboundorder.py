from odoo import api, fields, models, _
from odoo.exceptions import UserError


# 入库指令
class InboundOrder(models.Model):
    _name = 'panexlogi.inbound.order'
    _description = 'panexlogi.inbound.order'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = 'billno'

    billno = fields.Char(string='BillNo', readonly=True)
    date = fields.Date(string='Date（单据日期）', required=True, tracking=True, default=fields.Date.today)
    project = fields.Many2one('panexlogi.project', string='Project（项目）', required=True)
    project_code = fields.Char(string='Project Code', related='project.project_code', readonly=True)
    waybill_billno = fields.Many2one(comodel_name='panexlogi.waybill', string='Waybill NO')
    waybillno = fields.Char(string='B/L NUMBER', related='waybill_billno.waybillno', readonly=True, store=True)
    warehouse = fields.Many2one(comodel_name='stock.warehouse', string='Warehouse')
    warehouse_code = fields.Char(string='Warehouse Code', related='warehouse.code', readonly=True)
    cntrno = fields.Char(string='Container No')
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
    inbound_order_product_ids = fields.One2many('panexlogi.inbound.order.products', 'inboundorderid')

    @api.model
    def create(self, values):
        """
        生成跟踪单号
        """
        times = fields.Date.today()
        values['billno'] = self.env['ir.sequence'].next_by_code('seq.inbound.order', times)
        values['state'] = 'new'
        return super(InboundOrder, self).create(values)

    @api.onchange('waybill_billno')
    def _get_blno(self):
        for r in self:
            # r.waybillno = None
            if r.waybill_billno:
                r.waybillno = r.waybill_billno.waybillno

    @api.onchange('cntrno')
    def _get_productlist(self):
        """
                生成跟踪单号
                """
        args_list = []
        # products = ['Customs Clearance', 'Import Handling']
        if self.cntrno:
            product_id = self.env['panexlogi.waybill.packlist'].sudo().search(['&',
                                                                               ('cntrno', '=', self.cntrno),
                                                                               ('waybill_billno', '=',
                                                                                self.waybill_billno.id),])
            if product_id:
                for producta in product_id:
                    args_list.append((0, 0, {
                        'product_id': producta.product_id,
                        'powerperpc': producta.powerperpc,
                        'batch': producta.batch,
                        'pcs': producta.pcs,
                        'pallets': producta.pallets,
                        'cntrno':producta.cntrno
                    }))  # 建立odoo规定的关联关系！！
            self.inbound_order_product_ids = args_list  # 给关联字段赋值
