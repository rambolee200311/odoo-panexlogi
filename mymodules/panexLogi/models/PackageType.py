from odoo import models, fields


class PackageType(models.Model):
    _name = 'panexlogi.packagetype'
    _description = 'PackageType'
    _rec_name = "packagetype_name"

    packagetype_name = fields.Char(string='Package Type', required=True)
    remark = fields.Text(string='Remark')
