from odoo import models, fields, api
from odoo.exceptions import ValidationError


class Sender(models.Model):
    _name = 'panexlogi.sender'
    _description = 'Sender'
    _rec_name = "sender_name"

    sender_name = fields.Char(string='Name', required=True)
    tel = fields.Char(string='Phone', required=True)
    address = fields.Char(string='Address', required=True)


class Receiver(models.Model):
    _name = 'panexlogi.receiver'
    _description = 'Receiver'
    _rec_name = "receiver_name"

    receiver_name = fields.Char(string='Name', required=True)
    tel = fields.Char(string='Phone', required=True)
    address = fields.Char(string='Address', required=True)
