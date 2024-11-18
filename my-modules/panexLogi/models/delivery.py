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
    date = fields.Date(string='Date（预定日期）', readonly=True)
    project = fields.Many2one('panexlogi.project', string='Project（项目）')
    loading_ref = fields.Char(string='LOADING REFERENCE')
    consignee_ref = fields.Char(string='CONSIGNEE REFERENCE')
    load_address = fields.Char(string='LOAD ADDRESS')
    load_company_name = fields.Char(string='LOAD COMPANY NAME')
    load_contact_phone = fields.Char(string='LOAD Contact Phone')
    load_postcode = fields.Char(string='LOAD POSTCODE')
    load_country = fields.Many2one('res.country', 'LOAD COUNTRY')
    load_country_code = fields.Char('LOAD COUNTRY CODE', related='load_country.code')
    load_address_timeslot = fields.Char('LOAD ADDRESS TIMESLOT')
    unload_address = fields.Char(string='LOAD ADDRESS')
    unload_company_name = fields.Char(string='LOAD COMPANY NAME')
    unload_contact_phone = fields.Char(string='LOAD Contact Phone')
    unload_postcode = fields.Char(string='LOAD POSTCODE')
    unload_country = fields.Many2one('res.country', 'LOAD COUNTRY')
    unload_country_code = fields.Char('LOAD COUNTRY CODE', related='unload_country.code')
    delivery_address_timeslot = fields.Char('DELIVERY ADDRESS TIMESLOT')
    delivery_type = fields.Many2one('panexlogi.deliverytype', 'DELIVERY TYPE')
    loading_conditon = fields.Many2one('panexlogi.loadingcondition', 'LOADING CONDITIONS')
    unloading_conditon = fields.Many2one('panexlogi.loadingcondition', 'UNLOADING CONDITIONS')
    package_type = fields.Many2one('panexlogi.packagetype', 'PACKAGE TYPE')
    package_size = fields.Char('SIZE L*W*H')
    qty = fields.Integer('QTY')
    weight_per_unit = fields.Float('WEIGHT PER UNIT')
    gross_weight = fields.Float('GROSS WEIGHT')
    name_of_the_goods = fields.Char('NAME OF THE GOODS')
    uncode_class = fields.Char('UN CODE+CLASS')
    quote = fields.Float('QUOTE', default=0)
    charged = fields.Float('CHARGED', default=0)
    profit = fields.Float('PROFIT', default=0)
    trucker = fields.Many2one('res.partner', string='Trucker', domain=[('truck', '=', 'True')])

    planned_for_loading = fields.Datetime(string='Planned FOR LOADING')
    loading_date = fields.Datetime(string='LOADING DATE')
    delivery_date = fields.Datetime(string='DELIVERY DATE')
    extra_cost = fields.Float('Extra Cost', default=0)
    notes=fields.Text('Notes')
    @api.onchange('quote', 'charged','extra_cost')
    def _onchange_profit(self):
        self.profit = self.charged - self.quote-self.extra_cost

    @api.model
    def create(self, values):
        """
        生成跟踪单号
        """
        times = fields.Date.today()
        values['billno'] = self.env['ir.sequence'].next_by_code('seq.delivery', times)
        return super(Delivery, self).create(values)
