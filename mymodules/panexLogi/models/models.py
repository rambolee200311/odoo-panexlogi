# -*- coding: utf-8 -*-

# from odoo import models, fields, api


# class panex_logi(models.Model):
#     _name = 'panex_logi.panex_logi'
#     _description = 'panex_logi.panex_logi'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100
