# -*- coding: utf-8 -*-

# from odoo import models, fields, api


# class test-project2(models.Model):
#     _name = 'test-project2.test-project2'
#     _description = 'test-project2.test-project2'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100

