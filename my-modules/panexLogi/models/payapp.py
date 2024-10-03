from odoo import _, models, fields, api, exceptions
from odoo.exceptions import UserError


# 付款申请
class PaymentApplication(models.Model):
    _name = 'panexlogi.finance.paymentapplication'
    _description = 'panexlogi.finance.paymentapplication'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = 'billno'

    billno = fields.Char(string='Code', readonly=True)
    type = fields.Char(string='Type', readonly=True, default='Import')
    date = fields.Date(string='Date', required=True)
    payee = fields.Many2one('res.partner', string='Payee（收款方）', required=True, tracking=True)
    remark = fields.Text(string='Remark', tracking=True)
    pdffile = fields.Binary(string='File（原件）')
    pdffilename = fields.Char(string='File name')
    total_amount = fields.Float(string='Amount of Total（欧元金额）', compute='_compute_amount', tracking=True,
                                store=True)
    state = fields.Selection(
        selection=[
            ('new', 'New'),
            ('confirm', 'Confirm'),
            ('paid', 'Paid'),
            ('cancel', 'Cancel'),
        ],
        default='new',
        string="State",
        tracking=True
    )
    color = fields.Integer()
    paymentapplicationline_ids = fields.One2many('panexlogi.finance.paymentapplicationline', 'payapp_billno')

    @api.model
    def create(self, values):
        """
        生成跟踪单号
        ↓↓↓
        """
        times = fields.Date.today()
        values['billno'] = self.env['ir.sequence'].next_by_code('seq.finance.paymentapplication', times)
        values['state'] = 'new'
        return super(PaymentApplication, self).create(values)
    """
    confirm paid 状态下不可删除
    ↓↓↓    
    """
    def unlink(self):
        if self.state in ['confirm', 'paid']:
            raise UserError('You cannot delete a record with state: %s' % self.state)
        return super(PaymentApplication, self).unlink()

    @api.depends('paymentapplicationline_ids.amount')
    def _compute_amount(self):
        for rec in self:
            rec.total_amount = 0
            if rec.paymentapplicationline_ids:
                rec.total_amount = sum(rec.paymentapplicationline_ids.mapped('amount'))

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

    def action_paid_order(self):
        for rec in self:
            if rec.state != 'confirm':
                raise UserError(_("You only can paid Confirm Order"))
            else:
                rec.state = 'paid'
                return True

    def action_unpaid_order(self):
        for rec in self:
            if rec.state != 'paid':
                raise UserError(_("You only can unpaid Paid Order"))
            else:
                rec.state = 'confirm'
                return True

    def action_renew_order(self):
        for rec in self:
            if rec.state != 'cancel':
                raise UserError(_("You only can renew Concel Order"))
            else:
                rec.state = 'new'
                return True

    @api.depends('state')
    def _compute_can_unlink(self):
        for order in self:
            if order.state in ['confirm', 'paid']:
                order.can_unlink = False
            else:
                order.can_unlink = True

    can_unlink = fields.Boolean(string='Can Unlink', compute='_compute_can_unlink', store=True)


# 付款申请明细
class PaymentApplicationLine(models.Model):
    _name = 'panexlogi.finance.paymentapplicationline'
    _description = 'panexlogi.finance.paymentapplicationline'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = 'billno'

    billno = fields.Char(string='Code', readonly=True)
    invoiceno = fields.Char(string='Invoice No(发票号)', tracking=True)
    fitem = fields.Many2one('panexlogi.fitems', string='Item(费用项目)', tracking=True)
    fitem_name = fields.Char(string='Item Name(费用项目名称)', related='fitem.name', readonly=True)
    payapp_billno = fields.Many2one('panexlogi.finance.paymentapplication', tracking=True)
    amount = fields.Float(string='Amount（欧元金额）', tracking=True)
    remark = fields.Text(string='Remark', tracking=True)
    pdffile = fields.Binary(string='File（原件）')
    pdffilename = fields.Char(string='File name')

    @api.model
    def create(self, values):
        """
        生成跟踪单号
        """
        times = fields.Date.today()
        values['billno'] = self.env['ir.sequence'].next_by_code('seq.finance.paymentapplicationline', times)

        return super(PaymentApplicationLine, self).create(values)


# 进口付款申请
class ImportPaymentApplication(models.Model):
    _inherit = 'panexlogi.finance.paymentapplication'

    waybill_billno = fields.Many2one('panexlogi.waybill')


# 卡车付款申请
class CartagePaymentApplicationLine(models.Model):
    _inherit = 'panexlogi.finance.paymentapplicationline'

    cartagebillno = fields.Many2one('panexlogi.cartage')
