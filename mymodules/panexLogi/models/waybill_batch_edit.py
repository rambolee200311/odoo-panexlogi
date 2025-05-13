from odoo import _,models, fields, api
from odoo.exceptions import UserError


class WaybillBatchEditWizard(models.TransientModel):
    _name = 'panexlogi.waybill.batch.edit.wizard'
    _description = 'Waybill Batch Edit Wizard'

    waybill_id = fields.Many2one('panexlogi.waybill', string='Waybill', required=True)
    detail_ids = fields.Many2many(
        'panexlogi.waybill.details',
        string='Container Details',
        domain="[('waybill_billno', '=', waybill_id)]",
        relation='waybill_batch_edit_details_rel'  # Shorter table name
    )
    truck_type = fields.Selection(
        selection=[
            ('inbound', 'Inbound'),
            ('delivery', 'Delivery'),
            ('other', 'Other'),
        ],
        string='Truck Type',
        default='other',
        tracking=True,
        required=True
    )
    # warehouse
    warehouse = fields.Many2one('stock.warehouse', string='Warehouse')
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

    # delivery_address
    unload_address = fields.Many2one('panexlogi.address', string='Unload Address', tracking=True)
    delivery_address = fields.Char(string='Delivery Address',related='unload_address.street', tracking=True)
    delivery_company_name = fields.Char('Company Name', tracking=True,related='unload_address.company_name')
    delivery_contact_phone = fields.Char('contact_phone', tracking=True,related='unload_address.phone')
    delivery_postcode = fields.Char(string='Postcode', tracking=True,related='unload_address.postcode')
    delivery_country = fields.Many2one('res.country', 'Unload Country', tracking=True,related='unload_address.country')
    delivery_address_timeslot = fields.Char('Timeslot', tracking=True)
    delivery_type = fields.Many2one('panexlogi.deliverytype', 'Delivery Type', tracking=True)

    def apply_changes(self):
        for rec in self:
            for detail in rec.detail_ids:
                try:
                    # 强制转换 truck_type 为小写（与 Selection 选项匹配）
                    if rec.truck_type:
                        truck_type_lower = rec.truck_type.lower()
                        detail.write({
                            'truck_type': truck_type_lower,
                            'warehouse': rec.warehouse.id if rec.warehouse else False,
                        })
                    # 仅在 Truck Type 为 delivery 时更新 delivery 相关字段
                    if rec.truck_type == 'delivery' and rec.delivery_address:
                        detail.write({
                            'unload_address': rec.unload_address.id,
                            'delivery_address': rec.delivery_address,
                            'delivery_company_name': rec.delivery_company_name,
                            'delivery_contact_phone': rec.delivery_contact_phone,
                            'delivery_postcode': rec.delivery_postcode,
                            'delivery_country': rec.delivery_country.id,
                            'delivery_address_timeslot': rec.delivery_address_timeslot,
                            'delivery_type': rec.delivery_type.id,
                        })
                except UserError as e:
                    raise UserError(_("Failed to update container %s: %s") % (detail.cntrno, e))
        return {'type': 'ir.actions.act_window_close'}
