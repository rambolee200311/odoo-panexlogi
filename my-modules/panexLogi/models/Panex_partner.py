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
