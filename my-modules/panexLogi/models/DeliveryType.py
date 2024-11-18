from odoo import models, fields


class DeliveryType(models.Model):
    _name = 'panexlogi.deliverytype'
    _description = 'DeliveryType'
    _rec_name = "deliverytype_shortname"

    deliverytype_shortname = fields.Char(string='Short Name', required=True)
    deliverytype_name = fields.Char(string='Name', required=True)
