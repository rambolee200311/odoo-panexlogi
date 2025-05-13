from odoo import _, models, fields, api, exceptions
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)

class DeliveryDetail(models.Model):
    _name = 'panexlogi.delivery.detail'
    _description = 'panexlogi.delivery.detail'

    cntrno = fields.Char('Cantainer No')

    loading_ref = fields.Char(string='Loading Ref')
    load_address = fields.Many2one('panexlogi.address', 'Load Address')
    load_condition = fields.Many2one('panexlogi.loadingcondition', 'Load Condition')
    load_date = fields.Datetime(string='Load Date')
    load_timeslot = fields.Char('Load Timeslot')
    consignee_ref = fields.Char(string='Consignee Ref')
    unload_condition = fields.Many2one('panexlogi.loadingcondition', 'Unload Condition')
    unload_address = fields.Many2one('panexlogi.address', 'Unload Address')
    unload_timeslot = fields.Char('Unload Timeslot')
    unload_date = fields.Datetime(string='Unload Date')

    product = fields.Many2one('product.product', 'Product')
    product_name = fields.Char('Product Name', related='product.name', readonly=True)
    pallets = fields.Float('Palltes', default=1)
    qty = fields.Float('Pcs', default=1)
    batch_no = fields.Char('Batch No')
    model_type = fields.Char('Model Type')
    package_type = fields.Many2one('panexlogi.packagetype', 'Package Type')
    package_size = fields.Char('Size L*W*H')
    weight_per_unit = fields.Float('Weight PER Unit')
    gross_weight = fields.Float('Gross Weight')
    uncode = fields.Char('UN CODE')
    class_no = fields.Char('Class')
    deliveryid = fields.Many2one('panexlogi.delivery', 'Delivery ID')
    # 2025018 wangpeng 是否是ADR goods. 点是的话，就必须要填Uncode。 点选否的话，就不用必填UN code.
    adr = fields.Boolean(string='ADR')
    stackable = fields.Boolean(string='Stackable')
    remark = fields.Text('Remark')
    quote = fields.Float('Quote', default=0)  # 报价
    additional_cost = fields.Float('Additional Cost', default=0)  # 额外费用
    extra_cost = fields.Float('Extra Cost', default=0)  # 额外费用
    state = fields.Selection(
        selection=[
            ('new', 'New'),
            ('approve', 'Approve'),
            ('reject', 'Reject'),
            ('cancel', 'Cancel'),
            ('order', 'Order'),
        ],
        default='new',
        string="State",
        tracking=True
    )
    delivery_order_id = fields.Many2one('panexlogi.delivery.order', string='Delivery Order')
    waybill_detail_id = fields.Many2one('panexlogi.waybill.details', string='Waybill Detail ID')
    delivery_detail_cmr_id = fields.Many2one('panexlogi.delivery.detail.cmr', string='CMR ID')

    # Properly define company_id and exclude from tracking
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        tracking=False  # Explicitly disable tracking
    )

    # check is adr then uncode is required
    @api.constrains('adr', 'uncode')
    def _check_uncode_required(self):
        for record in self:
            if record.adr and not record.uncode:
                raise ValidationError(_("UN CODE is required when ADR is true."))

    # check that either loading_ref or cntrno is required
    #@api.constrains('loading_ref', 'cntrno')
    # def _check_loading_ref_or_cntrno(self):
    #     for record in self:
    #         if not record.loading_ref and not record.cntrno:
    #             raise ValidationError(_("Either Loading Ref or Container No is required."))

    def cancel_delivery_detail(self):
        for rec in self:
            if rec.delivery_order_id:
                raise UserError(_("This record is linked to a delivery order and cannot be canceled."))
            else:
                rec.state = 'cancel'
                return True
