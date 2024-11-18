from odoo import models, fields


class UnLoadingCondition(models.Model):
    _name = 'panexlogi.unloadingcondition'
    _description = 'UnLoadingCondition'
    # _rec_name = "unloadinglondition"

    unloadinglondition_name = fields.Char(string='UnLoading Condition', required=True)