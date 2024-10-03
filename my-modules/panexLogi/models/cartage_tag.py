# 卡车运单标签
from odoo import models, fields


class CartageTag(models.Model):
    _name = "panexlogi.cartage.tag"
    _description = "Catage Tag Model"
    _order = "name"

    name = fields.Char(
        required=True
    )
    color = fields.Integer(
        "Color"
    )

    _sql_constraints = {(
        'property_tag_unique', 'unique(name)', 'The Proprty Tag must be different!!'
    )}
