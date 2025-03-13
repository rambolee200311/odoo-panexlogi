from odoo import _, models, fields, api
from datetime import timedelta

from odoo.exceptions import UserError


# 到港通知wizard
class WaybillArrivNoticeWizard(models.TransientModel):
    _name = 'panexlogi.waybill.arrivnotice.wizard'
    _description = 'panexlogi.waybill.arrivnotice.wizard'

    eta = fields.Date(string='ETA', tracking=True)
    ata = fields.Date(string='ATA', tracking=True)
    terminal_a = fields.Many2one('panexlogi.terminal', string='Terminal of Arrival', tracking=True)
    eta_remark = fields.Text(string='Remark', tracking=True)
    ''''
    waybill_billno = fields.Char(string="BillNo")
    date = fields.Date(string='Date（到达日期）')
    blockdays = fields.Integer(string='Block days')
    pdffile = fields.Binary(string='File（原件）')
    '''

    @api.model
    def default_get(self, fields_list):
        res = super(WaybillArrivNoticeWizard, self).default_get(fields_list)
        # 获取当前上下文中的运单 ID
        active_id = self.env.context.get('active_id')
        if active_id:
            waybill = self.env['panexlogi.waybill'].browse(active_id)
            # 将已有值赋给向导字段
            res.update({
                'eta': waybill.eta,
                'ata': waybill.ata,
                'terminal_a': waybill.terminal_a.id,
                'eta_remark': waybill.eta_remark,
            })
        return res

    def update_existing_record(self):
        active_id = self.env.context.get('active_id')
        existing_record = self.env['panexlogi.waybill'].browse(active_id)
        if not existing_record:
            raise UserError("No existing record found with the given BillNo")
        # 修正字段名：terminal_a（原代码中写成了 terminal）
        existing_record.write({
            'eta': self.eta,
            'ata': self.ata,
            'terminal_a': self.terminal_a.id,  # 使用 terminal_a
            'eta_remark': self.eta_remark,
        })
        return {'type': 'ir.actions.act_window_close'}


# 到港通知

class WaybillArrivNotice(models.Model):
    _name = 'panexlogi.waybill.arrivnotice'
    _description = 'panexlogi.waybill.arrivnotice'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = 'billno'

    billno = fields.Char(string='Arrival Notice No', readonly=True)
    date = fields.Date(string='EDate（预计到达日期）', tracking=True, requeired=True)
    blockdays = fields.Integer(string='Block days', tracking=True, default=90)
    block_date = fields.Date(string='Block Date', compute='_get_block_date')
    adate = fields.Date(string='ADate（实际到达日期）', tracking=True)
    pdffile = fields.Binary(string='File（原件）')
    pdffilename = fields.Char(string='File name')
    waybill_billno = fields.Many2one('panexlogi.waybill')
    project = fields.Many2one('panexlogi.project', string='Project（项目）', compute='_get_waybill')
    shipping = fields.Char(string='Shipper（船公司）', compute='_get_waybill')
    # shipping_name = fields.Char(related='shipping.name', string='Shipper（船公司）')
    color = fields.Integer()
    state = fields.Selection(
        selection=[
            ('estimated', 'Estimated'),
            ('arrived', 'Arrived')
        ],
        default='estimated',
        string="State",
        tracking=True
    )
    terminal = fields.Many2one('panexlogi.terminal', string='Terminal')
    remark = fields.Text(string='Remark')

    @api.model
    def create(self, values):
        """
        生成跟踪单号
        """
        times = fields.Date.today()
        values['billno'] = self.env['ir.sequence'].next_by_code('seq.waybill.arrivnotice', times)
        return super(WaybillArrivNotice, self).create(values)

    @api.depends('date', 'blockdays')
    def _get_block_date(self):
        for record in self:
            if not (record.date and record.blockdays):
                record.block_date = record.date
                continue

            duration = timedelta(days=record.blockdays)
            record.block_date = record.date + duration
            pass

    @api.onchange('waybill_billno')
    def _get_waybill(self):
        for r in self:
            self.project = self.waybill_billno.project
            self.shipping = self.waybill_billno.shipping

    def action_confirm_order(self):
        for rec in self:
            if rec.state != 'new':
                raise UserError(_("You only can confirm New Order"))
            else:
                rec.state = 'confirm'
                return True

    def action_unconfirm_order(self):
        for rec in self:
            if rec.state != 'confirm':
                raise UserError(_("You only can unconfirm Confirmed Order"))
            else:
                rec.state = 'new'
                return True

    def action_cancel_order(self):
        for rec in self:
            if rec.state != 'new':
                raise UserError(_("You only can cancel New Order"))
            else:
                rec.state = 'cancel'
                return True

'''
# 到港通知 wizard

class WaybillArrivNoticeWizard(models.TransientModel):
    _name = 'panexlogi.waybill.arrivnotice.wizard'
    _description = 'panexlogi.waybill.arrivnotice.wizard'

    waybill_billno = fields.Char(string="BillNo")
    date = fields.Date(string='Date（到达日期）', required=True)
    blockdays = fields.Integer(string='Block days', required=True)
    pdffile = fields.Binary(string='File（原件）')
'''
