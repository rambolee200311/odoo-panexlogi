from odoo import models, fields, api


class Partner(models.Model):
    # _name = 'panex.shippingline'
    # _description = 'Shipping Line'

    _inherit = 'res.partner'

    panex_code = fields.Char(string='Contact Code')
    shipline = fields.Boolean("Shipping(船公司)", default=False)
    project = fields.Boolean("project（项目）", default=False)
    receiver = fields.Boolean("Receiver（收货方）", default=False)
    truck = fields.Boolean("Truck（卡车公司）", default=False)
    agency = fields.Boolean("Agency（代理）", default=False)


class Product(models.Model):
    _inherit = 'product.template'

    code = fields.Char(string='Code')
    net_weight = fields.Float(string='Net Weight')
    net_weight_unit = fields.Many2one('uom.uom', string='Net Weight Unit')
    gross_weight = fields.Float(string='Gross Weight')
    gross_weight_unit = fields.Many2one('uom.uom', string='Gross Weight Unit')
    volume = fields.Float(string='Volume')
    volume_unit = fields.Many2one('uom.uom', string='Volume Unit')
    width = fields.Float(string='Width')
    width_unit = fields.Many2one('uom.uom', string='Width Unit')
    height = fields.Float(string='Height')
    height_unit = fields.Many2one('uom.uom', string='Height Unit')
    depth = fields.Float(string='Depth')
    depth_unit = fields.Many2one('uom.uom', string='Depth Unit')
    size = fields.Char(string='Size')
    package = fields.Char(string='Package')
    k_number = fields.Char(string='K-Number')
    hs_code = fields.Char(string='HS Code')
    sku = fields.Char(string='SKU')
    model = fields.Char(string='Model')
