from odoo import api, fields, models, _
from odoo.exceptions import UserError


# 入库指令
class OutboundOrder(models.Model):
    _name = 'panexlogi.outbound.order'
    _description = 'panexlogi.outbound.order'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = 'billno'

    billno = fields.Char(string='BillNo', readonly=True)
    date = fields.Date(string='Date（单据日期）', required=True, tracking=True, default=fields.Date.today)
    project = fields.Many2one('panexlogi.project', string='Project（项目）', required=True)
    project_code = fields.Char(string='Project Code', related='project.project_code', readonly=True)
    warehouse = fields.Many2one(comodel_name='stock.warehouse', string='Warehouse')
    warehouse_code = fields.Char(string='Warehouse Code', related='warehouse.code', readonly=True)
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

    outbound_order_product_ids = fields.One2many('panexlogi.outbound.order.products', 'outboundorderid')

    unload_street = fields.Char(string='Unload Street')
    unload_city = fields.Char(string='Unload City')
    unload_state = fields.Char(string='Unload State')
    unload_zip = fields.Char(string='Unload Zip')
    unload_country = fields.Many2one('res.country', string='Unload Country')
    unload_company = fields.Char(string='Unload Company')
    unload_contact = fields.Char(string='Unload Contact')
    unload_phone = fields.Char(string='Unload Phone')
    unload_timeslot = fields.Char(string='Unload Timeslot')
    unload_date = fields.Datetime(string='Unload Date')
    unload_remark = fields.Text(string='Unload Remark')

    @api.model
    def create(self, values):
        """
        生成跟踪单号
        """
        times = fields.Date.today()
        values['billno'] = self.env['ir.sequence'].next_by_code('seq.outbound.order', times)
        values['state'] = 'new'
        return super(OutboundOrder, self).create(values)

    """
    @api.onchange('waybill_billno')
    def _get_blno(self):
        for r in self:
            # r.waybillno = None
            if r.waybill_billno:
                r.waybillno = r.waybill_billno.waybillno
    """
