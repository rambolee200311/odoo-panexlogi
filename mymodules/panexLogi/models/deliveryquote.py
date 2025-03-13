from datetime import datetime, timedelta
import pytz

from odoo import _, models, fields, api, exceptions
from odoo.exceptions import UserError, ValidationError


class DeliveryQuote(models.Model):
    _name = 'panexlogi.delivery.quote'
    _description = 'panexlogi.delivery.quote'
    _inherit = ["mail.thread", "mail.activity.mixin"]

    billno = fields.Char(string='BillNo', readonly=True)

    delivery_id = fields.Many2one('panexlogi.delivery', 'Delivery ID')
    date = fields.Date(string='Date', default=fields.Date.today())
    project = fields.Char(string='Project', related='delivery_id.project.project_code', readonly=True)
    deliveryquest_date = fields.Date(string='Request Date', related='delivery_id.date', readonly=True)
    planned_for_loading = fields.Datetime(string='Planned Loading', related='delivery_id.planned_for_loading',
                                          readonly=True)
    planned_for_unloading = fields.Datetime(string='Planned Unloading', related='delivery_id.planned_for_unloading',
                                            readonly=True)
    load_country = fields.Char(string='Load Country', related='delivery_id.load_country.name', readonly=True)
    unload_country = fields.Char(string='Unload Country', related='delivery_id.unload_country.name', readonly=True)
    load_address = fields.Char(string='Load Address', related='delivery_id.load_address', readonly=True)
    unload_address = fields.Char(string='Unload Address', related='delivery_id.unload_address', readonly=True)

    charged = fields.Float('Charged', default=0)  # 收费
    quote = fields.Float('Quote', default=0)  # 报价
    additional_cost = fields.Float('Additional Cost', default=0)  # 额外费用
    extra_cost = fields.Float('Extra Cost', default=0)  # 额外费用
    profit = fields.Float('Profit', default=0, readonly=True)  # 利润

    trucker = fields.Many2one('res.partner', string='Trucker', domain=[('truck', '=', 'True')])
    remark = fields.Text('Remark')

    deliverydetailids = fields.One2many('panexlogi.delivery.quote.detail', 'delivery_quote_id', 'Delivery Quote Detail')
    '''
    # Computed field to fetch related delivery details
    deliverydetailids = fields.One2many(
        'panexlogi.delivery.detail',
        compute='_compute_deliverydetailids',
        string='Delivery Details'
    )

    def _compute_deliverydetailids(self):
        for quote in self:
            # Fetch delivery details linked to the same delivery record
            quote.deliverydetailids = quote.delivery_id.deliverydetatilids
    '''


    state = fields.Selection(
        selection=[
            ('new', 'New'),
            ('approve', 'Approve'),
            ('reject', 'Reject'),
            ('cancel', 'Cancel'),
        ],
        default='new',
        string="State",
        tracking=True
    )

    @api.model
    def create(self, values):
        """
        生成跟踪单号
        """
        times = fields.Date.today()
        values['billno'] = self.env['ir.sequence'].next_by_code('seq.delivery.quote', times)
        return super(DeliveryQuote, self).create(values)

    @api.onchange('delivery_id')
    def _onchange_delivery_id(self):
        self.project = self.delivery_id.project.project_code
        self.deliveryquest_date = self.delivery_id.date
        self.planned_for_loading = self.delivery_id.planned_for_loading
        self.planned_for_unloading = self.delivery_id.planned_for_unloading
        self.load_country = self.delivery_id.load_country.name
        self.unload_country = self.delivery_id.unload_country.name
        self.load_address = self.delivery_id.load_address
        self.unload_address = self.delivery_id.unload_address
        lines = []
        for rec in self.delivery_id.deliverydetatilids:
            lines.append((0, 0, {
                'loading_ref': rec.loading_ref,
                'cntrno': rec.cntrno,
                'quote': rec.quote,
                'additional_cost': rec.additional_cost,
                'extra_cost': rec.extra_cost,
                'product': rec.product.id,
                'qty': rec.qty,
                'package_type': rec.package_type.id,
                'package_size': rec.package_size,
                'weight_per_unit': rec.weight_per_unit,
                'gross_weight': rec.gross_weight,
                'uncode': rec.uncode,
                'class_no': rec.class_no,
                'deliveryid': rec.deliveryid.id,
                'adr': rec.adr,
                'remark': rec.remark,
            }))
        self.deliverydetailids = lines

    def action_approve_order(self):
        for rec in self:
            if rec.state != 'new':
                raise UserError(_("You only can approve New quote"))
            else:
                rec.delivery_id.quote = rec.quote
                rec.delivery_id.trucker = rec.trucker
                rec.delivery_id.additional_cost = rec.additional_cost
                rec.delivery_id._onchange_profit()
                rec.state = 'approve'
                return True
    def action_reject_order(self):
        for rec in self:
            if rec.state != 'new':
                raise UserError(_("You only can reject New quote"))
            else:
                rec.state = 'reject'
                return True


    def action_cancel_order(self):
        for rec in self:
            rec.state = 'cancel'
            return True

    def on_unlink(self):
        if self.state != 'cancel':
            raise UserError(_("You can not delete approved or rejected quote, try to cancel it first"))


class DeliveryQuotDetail(models.Model):
    _name = 'panexlogi.delivery.quote.detail'
    _description = 'panexlogi.delivery.quote.detail'

    delivery_quote_id = fields.Many2one('panexlogi.delivery.quote', 'Delivery Quote ID')

    loading_ref = fields.Char(string='Loading Ref')
    cntrno = fields.Char('Cantainer No')
    quote = fields.Float('Quote', default=0)  # 报价
    additional_cost = fields.Float('Additional Cost', default=0)  # 额外费用
    extra_cost = fields.Float('Extra Cost', default=0)  # 额外费用
    product = fields.Many2one('product.product', 'Product')
    product_name = fields.Char('Product Name', related='product.name', readonly=True)
    qty = fields.Float('Quantity', default=1)
    package_type = fields.Many2one('panexlogi.packagetype', 'Package Type')
    package_size = fields.Char('Size L*W*H')
    weight_per_unit = fields.Float('Weight PER Unit')
    gross_weight = fields.Float('Gross Weight')
    uncode = fields.Char('UN CODE')
    class_no = fields.Char('Class')
    deliveryid = fields.Many2one('panexlogi.delivery', 'Delivery ID')
    # 2025018 wangpeng 是否是ADR goods. 点是的话，就必须要填Uncode。 点选否的话，就不用必填UN code.
    adr = fields.Boolean(string='ADR')
    remark = fields.Text('Remark')
