from odoo import models, fields


class Country(models.Model):
    _name = 'panexlogi.country'
    _description = 'Country'
    _rec_name = "country_shortname"

    country_shortname = fields.Char(string='Short Name', required=True)
    country_name = fields.Char(string='Country Name', required=True)
