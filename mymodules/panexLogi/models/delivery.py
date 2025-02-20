from datetime import datetime, timedelta
import pytz

from odoo import _, models, fields, api, exceptions
from odoo.exceptions import UserError, ValidationError


# 卡车运单
class Delivery(models.Model):
    _name = 'panexlogi.delivery'
    _description = 'panexlogi.delivery'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = 'billno'

    billno = fields.Char(string='BillNo', readonly=True)
    date = fields.Date(string='Date', default=fields.Date.today())
    project = fields.Many2one('panexlogi.project', string='Project（项目）')

    inner_ref = fields.Char(string='Inner Ref')
    loading_ref = fields.Char(string='Loading Ref')
    consignee_ref = fields.Char(string='Consignee Ref')
    load_address = fields.Char(string='Address')
    load_company_name = fields.Char(string='Company Name')
    load_contact_phone = fields.Char(string='Contact Phone')
    load_postcode = fields.Char(string='Postcode')
    load_country = fields.Many2one('res.country', 'Load Coutry')
    load_country_code = fields.Char('Country Code', related='load_country.code')
    load_address_timeslot = fields.Char('Timeslot')
    unload_address = fields.Char(string='Address')
    unload_company_name = fields.Char(string='Company Name')
    unload_contact_phone = fields.Char(string='Contact Phone')
    unload_postcode = fields.Char(string='Postcode')
    unload_country = fields.Many2one('res.country', 'Unload Country')
    unload_country_code = fields.Char('Country Codde', related='unload_country.code')
    unload_address_timeslot = fields.Char('Timeslot')
    delivery_type = fields.Many2one('panexlogi.deliverytype', 'Delivery Type')
    loading_conditon = fields.Many2one('panexlogi.loadingcondition', ' Condition')
    unloading_conditon = fields.Many2one('panexlogi.loadingcondition', 'Condition')
    planned_for_loading = fields.Datetime(string='Planned Loading')
    planned_for_unloading = fields.Datetime(string='Planned Unloading')

    quote = fields.Float('Quote', default=0, tracking=True, readonly=True)
    charged = fields.Float('Charged', default=0, tracking=True)
    profit = fields.Float('Profit', default=0)
    trucker = fields.Many2one('res.partner', string='Trucker', domain=[('truck', '=', 'True')])

    loading_date = fields.Datetime(string='Loading Date')
    # delivery_date = fields.Datetime(string='Delivery Date')
    unloading_date = fields.Datetime(string='Unloading Date')

    additional_cost = fields.Float('Additional Cost', default=0, tracking=True, readonly=True)  # 额外费用
    extra_cost = fields.Float('Extra Cost', default=0, tracking=True, readonly=True)
    notes = fields.Text('Notes')
    deliverydetatilids = fields.One2many('panexlogi.delivery.detail', 'deliveryid', 'Delivery Detail')
    deliveryquoteids = fields.One2many('panexlogi.delivery.quote', 'delivery_id', 'Delivery Quote')
    deliverystatusids = fields.One2many('panexlogi.delivery.status', 'delivery_id', 'Delivery Status')

    pdffile = fields.Binary(string='POD File')
    pdffilename = fields.Char(string='POD File name')

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

    def action_confirm_order(self):
        for rec in self:
            if rec.state != 'new':
                raise UserError(_("You only can confirm New Order"))
            else:
                rec.state = 'confirm'
                return True

    def action_unconfirm_order(self):
        for rec in self:
            if rec.state != 'confirm':
                raise UserError(_("You only can unconfirm Confirmed Order"))
            else:
                rec.state = 'new'
                return True

    def action_cancel_order(self):
        for rec in self:
            if rec.state != 'new':
                raise UserError(_("You only can cancel New Order"))
            else:
                rec.state = 'cancel'
                return True

    @api.onchange('quote', 'charged', 'extra_cost', 'additional_cost')
    def _onchange_profit(self):
        for r in self:
            r.profit = r.charged - r.quote - r.extra_cost - r.additional_cost

    @api.model
    def create(self, values):
        """
        生成跟踪单号
        """
        times = fields.Date.today()
        values['billno'] = self.env['ir.sequence'].next_by_code('seq.delivery', times)
        return super(Delivery, self).create(values)

    # 跳转wizard视图
    def add_delivery_status(self):
        return {
            'name': 'Add Status',
            'type': 'ir.actions.act_window',
            'res_model': 'panexlogi.delivery.status.wizard',
            'view_mode': 'form',
            'target': 'new',
        }

    # recalculate extra cost
    def _get_extra_cost(self):
        extra_cost = 0
        for r in self.deliverystatusids:
            extra_cost += r.extra_cost
        self.extra_cost = extra_cost




class DeliveryDetail(models.Model):
    _name = 'panexlogi.delivery.detail'
    _description = 'panexlogi.delivery.detail'
    _inherit = ["mail.thread", "mail.activity.mixin"]

    product = fields.Many2one('product.product', 'Product')
    product_name = fields.Char('Product Name', related='product.name', readonly=True)
    qty = fields.Float('Quantity', default=1)
    package_type = fields.Many2one('panexlogi.packagetype', 'Package Type')
    package_size = fields.Char('Size L*W*H')
    weight_per_unit = fields.Float('Weight PER Unit')
    gross_weight = fields.Float('Gross Weight')

    uncode = fields.Char('UN CODE')
    class_no = fields.Char('Class')
    cntrno = fields.Char('Cantainer No')
    deliveryid = fields.Many2one('panexlogi.delivery', 'Delivery ID')
    # 2025018 wangpeng 是否是ADR goods. 点是的话，就必须要填Uncode。 点选否的话，就不用必填UN code.
    adr = fields.Boolean(string='ADR')
    remark = fields.Text('Remark')

    @api.constrains('adr', 'uncode')
    def _check_uncode_required(self):
        for record in self:
            if record.adr and not record.uncode:
                raise ValidationError(_("UN CODE is required when ADR is true."))


class DeliveryStatus(models.Model):
    _name = 'panexlogi.delivery.status'
    _description = 'panexlogi.delivery.status'
    _inherit = ["mail.thread", "mail.activity.mixin"]

    delivery_id = fields.Many2one('panexlogi.delivery', 'Delivery ID')
    date = fields.Datetime('Date', default=fields.Datetime.now(), tracking=True)
    extra_cost = fields.Float('Extra Cost', default=0)
    status = fields.Char('Status', tracking=True)
    description = fields.Text('Description')


'''
    @api.onchange('extra_cost')
    def _get_proft(self):
        for r in self:
            if r._origin.extra_cost:
                r.delivery_id.extra_cost += r.extra_cost-r._origin.extra_cost
            else:
                r.delivery_id.extra_cost += r.extra_cost

            r.delivery_id._onchange_profit()

'''


class DeliveryStatusWizard(models.TransientModel):
    _name = 'panexlogi.delivery.status.wizard'
    _description = 'panexlogi.delivery.status.wizard'

    date = fields.Datetime('Date', default=fields.Datetime.now())
    extra_cost = fields.Float('Extra Cost', default=0)
    status = fields.Selection(
        selection=[
            ('order', 'Order Placed'),
            ('transit', 'In Transit'),
            ('delivery', 'Delivered'),
            ('cancel', 'Cancel'),
            ('return', 'Return'),
            ('other', 'Other'),
            ('complete', 'Complete'),
        ],
        default='order',
        string='status',
        tracking=True
    )
    description = fields.Text('Description')

    def add_line(self):
        self.env['panexlogi.delivery.status'].sudo().create({
            'date': self.date,
            'status': self.status,
            'extra_cost': self.extra_cost,
            'description': self.description,
            'delivery_id': self.env.context.get('active_id'),
        })
        domain = []
        domain.append(('id', '=', self.env.context.get('active_id')))
        self.env['panexlogi.delivery'].sudo().search(domain)._get_extra_cost()
        self.env['panexlogi.delivery'].sudo().search(domain)._onchange_profit()
        return {'type': 'ir.actions.act_window_close'}
