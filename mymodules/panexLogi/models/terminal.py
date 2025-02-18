from odoo import models, fields


class Terminal(models.Model):
    _name = 'panexlogi.terminal'
    _description = 'Terminal'
    _rec_name = "terminal_code"

    terminal_code = fields.Char(string='Code', required=True)
    terminal_name = fields.Char(string='Name')
    terminal_address = fields.Char(string='Address')
