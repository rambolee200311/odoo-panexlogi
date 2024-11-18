from odoo import models, fields, api


class Waybill_project1(models.Model):
    _name = 'panexwd.europe.waybill.project1'
    _description = 'panexwd.europe.waybill.project1'
    # _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = 'billno'

    p1_billno = fields.Char(string='BillNo', readonly=True)
    parent_id = fields.Many2one(
        'panexwd.europe.waybill',
        delegate=True,
        ondelete='cascade',
        required=True)

    @api.model
    def create(self, values):
        """
        生成跟踪单号
        """

        times = fields.Date.today()
        values['p1_billno'] = self.env['ir.sequence'].next_by_code('seq.waybill.project1', times)

        values['project'] = 'project1'
        return super(Waybill_project1, self).create(values)


