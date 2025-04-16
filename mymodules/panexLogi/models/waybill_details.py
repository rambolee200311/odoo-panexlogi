from odoo import _, models, fields, api
from datetime import timedelta

from odoo.exceptions import UserError


# 货柜明细

class WaybillDetails(models.Model):
    _name = 'panexlogi.waybill.details'
    _description = 'panexlogi.waybill.details'
    _inherit = ["mail.thread", "mail.activity.mixin"]

    uncode = fields.Char('UN CODE', tracking=True)
    cntrno = fields.Char(string='Container No', tracking=True)
    cntrnum = fields.Integer(string='Contrainer Num', default=1)
    pallets = fields.Float(string='Pallets', default=26)
    note = fields.Text(string='Note')

    waybill_billno = fields.Many2one('panexlogi.waybill')

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
    product_info = fields.Char(string='Product Info', tracking=True)
    pcs = fields.Float(string='Pcs', default=1, tracking=True)
    truck_type = fields.Selection(
        selection=[
            ('inbound', 'Inbound'),
            ('delivery', 'Delivery'),
            ('other', 'Other'),
        ],
        string='Truck Type',
        default='other',
        tracking=True
    )
    warehouse = fields.Many2one(
        'stock.warehouse',
        string='Warehouse',
        tracking=True
    )
    warehouse_address_street = fields.Char(
        string='Warehouse Address Street',
        related='warehouse.partner_id.street',
        readonly=True
    )
    warehouse_address_city = fields.Char(
        string='Warehouse Address City',
        related='warehouse.partner_id.city',
        readonly=True
    )
    warehouse_address_state = fields.Char(
        string='Warehouse Address State',
        related='warehouse.partner_id.state_id.name',
        readonly=True
    )
    warehouse_address_country = fields.Char(
        string='Warehouse Address Country',
        related='warehouse.partner_id.country_id.name',
        readonly=True
    )
    warehouse_address_zip = fields.Char(
        string='Warehouse Address Zip',
        related='warehouse.partner_id.zip',
        readonly=True
    )
    warehouse_phone = fields.Char(
        string='Warehouse Phone',
        related='warehouse.partner_id.phone',
        readonly=True
    )
    warehouse_mobile = fields.Char(
        string='Warehouse Mobile',
        related='warehouse.partner_id.mobile',
        readonly=True
    )
    delivery_address = fields.Char(string='Address', tracking=True)
    delivery_company_name = fields.Char('Company Name', tracking=True)
    delivery_contact_phone = fields.Char('contact_phone', tracking=True)
    delivery_postcode = fields.Char(string='Postcode', tracking=True)
    delivery_country = fields.Many2one('res.country', 'Unload Country', tracking=True)
    delivery_address_timeslot = fields.Char('Timeslot', tracking=True)
    delivery_type = fields.Many2one('panexlogi.deliverytype', 'Delivery Type', tracking=True)

    waybill_packlist_id = fields.One2many('panexlogi.waybill.packlist', 'waybll_detail_id', string='Packing List')

    @api.model
    def name_get(self):
        """正确返回 (id, cntrno) 结构，避免多余字段"""
        return [(record.id, record.cntrno or f"Container ({record.id})") for record in self]

    # check if waybill_billno.adr=ture then uncode is required
    @api.constrains('uncode')
    def _check_uncode(self):
        for rec in self:
            if rec.waybill_billno.adr and not rec.uncode:
                raise UserError(_("UN Code is required!"))
"""
    # check if truck_type=inbound then warehouse is required
    @api.constrains('truck_type', 'warehouse')
    def _check_truck_type_warehouse(self):
        for rec in self:
            if rec.truck_type == 'inbound' and not rec.warehouse:
                raise UserError(_("Warehouse is required!"))

    # check if truck_type=delivery then delivery_address is required
    @api.constrains('truck_type', 'delivery_address')
    def _check_truck_type_delivery(self):
        for rec in self:
            if rec.truck_type == 'delivery' and not rec.delivery_address:
                raise UserError(_("Delivery Address is required!"))
"""