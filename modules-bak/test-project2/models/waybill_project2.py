from odoo import models, fields, api


class Waybill_project2(models.Model):
    _name = 'panexwd.europe.waybill.project2'
    _description = 'panexwd.europe.waybill.project2'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = 'billno'

    p2_billno = fields.Char(string='BillNo', readonly=True)
    parent_id = fields.Many2one(
        'panexwd.europe.waybill',
        delegate=True,
        ondelete='cascade',
        required=True)
    p2_charDef1 = fields.Char(string='charDef1', required=True)

    @api.onchange('p2_charDef1')
    def onchange_p2_charDef1(self):
        if self.p2_charDef1:
            self.parent_id.charDef1 = self.p2_charDef1

    @api.model
    def create(self, values):
        """
        生成跟踪单号
        """

        times = fields.Date.today()
        values['p2_billno'] = self.env['ir.sequence'].next_by_code('seq.waybill.project2', times)

        values['project'] = 'project2'
        return super(Waybill_project2, self).create(values)


