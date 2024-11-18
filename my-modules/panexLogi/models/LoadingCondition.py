from odoo import models, fields


class LoadingCondition(models.Model):
    _name = 'panexlogi.loadingcondition'
    _description = 'LoadingCondition'
    # _rec_name = "loadingcondition"

    loadingcondition_name = fields.Char(string='Name', required=True)
    beload = fields.Boolean(string='Load')
    beunload = fields.Boolean(string='Unload')
