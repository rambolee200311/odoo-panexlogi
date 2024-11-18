from odoo import _, models, fields, api
from odoo.exceptions import UserError


# 提单
class Waybill(models.Model):
    _name = 'panexwd.europe.waybill'
    _description = 'panexwd.europe.waybill'
    # _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = 'billno'

    billno = fields.Char(string='BillNo', readonly=True)
    project = fields.Char(string='Project（项目）')
    date = fields.Date(string='Date（提单日期）', required=True, tracking=True, default=fields.Date.today)

    color = fields.Integer()
    state = fields.Selection(
        selection=[
            ('new', 'New'),
            ('confirm', 'Confirm'),
            ('cancel', 'Cancel'),
        ],
        default='new',
        string="State",
        tracking=True
    )


    charDef1 = fields.Char(string='charDef1')
    charDef2 = fields.Char(string='charDef2')
    charDef3 = fields.Char(string='charDef3')
    charDef4 = fields.Char(string='charDef4')

    @api.model
    def create(self, values):
        """
        生成跟踪单号
        """
        times = fields.Date.today()
        values['billno'] = self.env['ir.sequence'].next_by_code('seq.waybill', times)
        values['state'] = 'new'
        return super(Waybill, self).create(values)
