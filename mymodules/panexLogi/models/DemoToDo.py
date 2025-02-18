from odoo import _, models, fields, api
from datetime import timedelta
from datetime import datetime
from odoo.exceptions import UserError


# 到港通知

class DemoToDo(models.Model):
    _name = 'panexlogi.demotodo'
    _description = 'panexlogi.demotodo'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = 'billno'

    billno = fields.Char(string='Bill No', readonly=True)
    project = fields.Many2one('panexlogi.project', string='Project（项目）', required=True, tracking=True)
    receiver = fields.Many2one('res.users', 'receiver', tracking=True)
    date = fields.Date(string='start date', tracking=True)
    ddate = fields.Date(string='Deadline Date', tracking=True)
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

    iCron = fields.Integer(default=0, readonly=True)
    packlists=fields.One2many('panexlogi.demotodo.packlist','demotodono',string='Packing List')

    @api.model
    def create(self, values):
        """
        生成跟踪单号
        """
        times = fields.Date.today()
        values['billno'] = self.env['ir.sequence'].next_by_code('seq.demotodo', times)
        res = super(DemoToDo, self).create(values)
        """
        duration = timedelta(days=5)
        date_deadline = res.ddate - duration
        res.activity_schedule('mail.mail_activity_data_todo', summary='到期提醒', date_deadline=date_deadline,
                              user_id=res.receiver.id)
        """
        return res

    def action_confirm_order(self):
        for rec in self:
            if rec.state != 'new':
                raise UserError(_("You only can confirm New Order"))
            else:
                rec.state = 'confirm'
                # body = '审核通过'
                # self.sudo().message_post(body=body, message_type='notification')

                return True

    def action_unconfirm_order(self):
        for rec in self:
            if rec.state != 'confirm':
                raise UserError(_("You only can unconfirm Confirmed Order"))
            else:
                rec.state = 'new'
                # body = '取消审核'
                # self.sudo().message_post(body=body, message_type='comment')

                return True

    def action_cancel_order(self):
        for rec in self:
            if rec.state != 'new':
                raise UserError(_("You only can cancel New Order"))
            else:
                rec.state = 'cancel'
                return True

    def _action_cron_demo(self):
        res = self.env['panexlogi.demotodo'].search([])
        for rec in res:
            if rec.state == 'new':
                if rec.iCron < 1:
                    duration = timedelta(days=3)
                    date_deadline = rec.date + duration
                    date_now = datetime.date(datetime.now())
                    if date_deadline <= date_now:  # fields.Date.today():
                        rec.activity_schedule('mail.mail_activity_data_todo', summary='单据已经提交3天，请尽快审核',
                                              date_deadline=date_deadline + duration,
                                              user_id=rec.receiver.id)
                        rec.iCron = 1
        return True


class DemoToDoPackList(models.Model):
    _name = 'panexlogi.demotodo.packlist'
    _description = 'panexlogi.demotodo.packlist'

    product_id = fields.Many2one('product.product', string='Product', domain=[('categ_id', '=', 11)])
    totalpieces = fields.Integer(string='Total pieces', required=True, tracking=True)
    package = fields.Integer(string='Package')
    grossweight = fields.Float(string='Gross Weight(KG)')
    netweight = fields.Float(string='Net Weight(KG)')
    eurtotal = fields.Float(string='Total_of_EUR', required=True, tracking=True)
    demotodono = fields.Many2one('panexlogi.demotodo')