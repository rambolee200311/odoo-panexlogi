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

    quote = fields.Float('Quote', default=0)
    charged = fields.Float('Charged', default=0)
    profit = fields.Float('Profit', default=0)
    trucker = fields.Many2one('res.partner', string='Trucker', domain=[('truck', '=', 'True')])

    loading_date = fields.Datetime(string='Loading Date')
    # delivery_date = fields.Datetime(string='Delivery Date')
    unloading_date = fields.Datetime(string='Unloading Date')

    extra_cost = fields.Float('Extra Cost', default=0)
    notes = fields.Text('Notes')
    deliverydetatilids = fields.One2many('panexlogi.delivery.detail', 'deliveryid', 'Delivery Detail')
    deliveryquoteids = fields.One2many('panexlogi.delivery.quote', 'delivery_id', 'Delivery Quote')

    @api.onchange('quote', 'charged', 'extra_cost')
    def _onchange_profit(self):
        self.profit = self.charged - self.quote - self.extra_cost

    @api.model
    def create(self, values):
        """
        生成跟踪单号
        """
        times = fields.Date.today()
        values['billno'] = self.env['ir.sequence'].next_by_code('seq.delivery', times)
        return super(Delivery, self).create(values)


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

    uncode_class = fields.Char('UN CODE+CLASS')
    cntrno = fields.Char('Cantainer No')
    deliveryid = fields.Many2one('panexlogi.delivery', 'Delivery ID')


