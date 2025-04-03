from odoo import _, models, fields, api, exceptions
from odoo.exceptions import UserError


# 结算方式
class PaymentMethod(models.Model):
    _name = 'panexlogi.finance.payment.method'
    _description = 'panexlogi.finance.payment.method'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = 'name'

    code = fields.Char(string='Code (length=2)', required=True)
    name = fields.Char(string='Name', required=True)
    state = fields.Selection([('active', 'Active'), ('cancel', 'Cancel')], string='State', default='active')

    # check method code
    @api.constrains('code')
    def _check_code(self):
        for rec in self:
            if rec.code and len(rec.code) != 2:
                raise exceptions.ValidationError(_("Code must be 2 characters long!"))
            if rec.code and rec.code.isalnum() == False:
                raise exceptions.ValidationError(_("Code must be alphanumeric!"))
            # check if code is unique
            if rec.code:
                if self.env['panexlogi.finance.payment.method'].search_count(
                        [('code', '=', rec.code), ('state', '!=', 'cancel')]) > 1:
                    raise exceptions.ValidationError(_("Code must be unique!"))

    # check method name
    @api.constrains('name')
    def _check_name(self):
        # check if name is unique or empty
        for rec in self:
            if not rec.name:
                raise exceptions.ValidationError(_("Name must be filled!"))
            if rec.name:
                if self.env['panexlogi.finance.payment.method'].search_count(
                        [('name', '=', rec.name), ('state', '!=', 'cancel')]) > 1:
                    raise exceptions.ValidationError(_("Name must be unique!"))

    # dont allow user unlink record
    def unlink(self):
        for rec in self:
            raise UserError(_("You can not delete active record!"))

    # cancel the record
    def action_cancel(self):
        for rec in self:
            rec.state = 'cancel'

    # active the record
    def action_active(self):
        for rec in self:
            rec.state = 'active'


# 付款单
class Payment(models.Model):
    _name = 'panexlogi.finance.payment'
    _description = 'panexlogi.finance.payment'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = 'billno'

    billno = fields.Char(string='Code', readonly=True)
    type = fields.Char(string='Type', readonly=True, default='Import')
    payee = fields.Many2one('res.partner', string='Payee（收款方）',
                            required=True, tracking=True, readonly=True)
    # payee_bank =fields.Char(string='Bank（收款方银行）', tracking=True)
    payee_account = fields.Char(string='Account（收款方账号）', tracking=True)
    payee_account_partner = fields.Many2one('res.partner.bank', string='Account（收款方账号）', tracking=True,
                                            domain="[('partner_id', '=', payee)]")
    payee_account_number = fields.Char(string='IBAN（收款方账号IBAN）', related='payee_account_partner.acc_number',
                                       readonly=True)
    payee_bank_bic = fields.Char(string='Bank BIC（收款方银行BIC）', related='payee_account_partner.bank_bic',
                                 readonly=True)

    payer = fields.Char(string='Payer（付款方）', tracking=True)
    payer_bank = fields.Char(string='Bank（付款方银行）', tracking=True)
    payer_account = fields.Char(string='Account（付款方账号）', tracking=True)
    payment_method = fields.Many2one('panexlogi.finance.payment.method',
                                     string='Payment Method（付款方式）',
                                     domain=[('state', '=', 'active')], tracking=True)
    pay_date = fields.Date(string='Date(付款日期)', tracking=True)
    pay_amount = fields.Float(string='Amount（欧元金额）', tracking=True, compute='_compute_amount', stock=True)
    pay_amount_usd = fields.Float(string='Amount（美元金额）', tracking=True, compute='_compute_amount', stock=True)
    pay_remark = fields.Text(string='Remark', tracking=True)
    pay_pdffile = fields.Binary(string='File（原件）')
    pay_pdffilename = fields.Char(string='File name')
    state = fields.Selection([
        ('new', 'New'),
        ('confirm', 'Confirm'),
        ('paid', 'Paid'),
        ('cancel', 'Cancel')
    ], string='State', default='new')
    paymentline_ids = fields.One2many('panexlogi.finance.payment.line', 'payment_id')
    projects = fields.Char(string='Projects', compute='_compute_projects', store=True)
    invoicenos = fields.Char(string='Invoice Nos', compute='_compute_projects', store=True)
    # shows distinct panexlogi.finance.payment.line.project.name,
    @api.depends('paymentline_ids.project')
    def _compute_projects(self):
        for rec in self:
            project_names = rec.paymentline_ids.mapped('project.project_name')
            invoicenos = rec.paymentline_ids.mapped('invoiceno')
            distinct_project_names = list(set(project_names))
            distinct_invoicenos = list(set(invoicenos))
            rec.projects = ', '.join(distinct_project_names)
            rec.invoicenos = ', '.join(distinct_invoicenos)

    @api.model
    def create(self, values):
        """
        生成跟踪单号
        ↓↓↓
        """
        times = fields.Date.today()
        values['billno'] = self.env['ir.sequence'].next_by_code('seq.finance.payment', times)
        values['state'] = 'new'
        return super(Payment, self).create(values)

    """
        confirm paid 状态下不可删除
        ↓↓↓    
        """

    def unlink(self):
        # Check if record is in confirm or paid state
        if self.state in ['confirm', 'paid']:
            raise UserError('You cannot delete a record with state: %s' % self.state)
        # Delete related payment lines
        for payment in self:
            # Delete related payment lines
            payment.paymentline_ids.unlink()
        # Delete the record
        return super(Payment, self).unlink()

    @api.depends('paymentline_ids')
    def _compute_amount(self):
        for rec in self:
            rec.pay_amount = 0
            rec.pay_amount_usd = 0
            if rec.paymentline_ids:
                rec.pay_amount = sum(rec.paymentline_ids.mapped('pay_amount'))
                rec.pay_amount_usd = sum(rec.paymentline_ids.mapped('pay_amount_usd'))

    def action_confirm_order(self):
        for rec in self:
            if rec.state != 'new':
                raise UserError(_("You only can confirm New Payment"))
            else:
                rec.state = 'confirm'
                return True

    def action_unconfirm_order(self):
        for rec in self:
            if rec.state != 'confirm':
                raise UserError(_("You only can unconfirm Confirmed Payment"))
            else:
                rec.state = 'new'
                return True

    def action_cancel_order(self):
        for rec in self:
            if rec.state != 'new':
                raise UserError(_("You only can cancel New Payment"))
            else:
                rec.state = 'cancel'
                # CANCLE PAYMENT APPLICATION
                for line in rec.paymentline_ids:
                    paymentapplication = self.env['panexlogi.finance.paymentapplication'].search(
                        [('payment_id', '=', rec.id), ('state', '=', 'apply')])
                    if paymentapplication:
                        for application in paymentapplication:
                            if line.source == application.type and line.source_code == application.billno:
                                application.payment_id = False
                return True

    def action_paid_order(self):
        for rec in self:
            if rec.state != 'confirm':
                raise UserError(_("You only can paid Confirm Payment"))
            else:
                rec.state = 'paid'
                # PAID PAYMENT APPLICATION
                for line in rec.paymentline_ids:
                    paymentapplication = self.env['panexlogi.finance.paymentapplication'].search(
                        [('payment_id', '=', rec.id), ('state', '=', 'confirm')])
                    if paymentapplication:
                        for application in paymentapplication:
                            if line.source == application.type and line.source_code == application.billno:
                                application.state = 'paid'
                return True

    def action_unpaid_order(self):
        for rec in self:
            if rec.state != 'paid':
                raise UserError(_("You only can unpaid Paid Payment"))
            else:
                rec.state = 'confirm'
                # UNPAID PAYMENT APPLICATION
                for line in rec.paymentline_ids:
                    paymentapplication = self.env['panexlogi.finance.paymentapplication'].search(
                        [('payment_id', '=', rec.id), ('state', '=', 'paid')])
                    if paymentapplication:
                        for application in paymentapplication:
                            if line.source == application.type and line.source_code == application.billno:
                                application.state = 'confirm'
                return True

    def action_renew_order(self):
        for rec in self:
            if rec.state != 'cancel':
                raise UserError(_("You only can renew Cancel Payment"))
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


# 付款单明细
class PaymentLine(models.Model):
    _name = 'panexlogi.finance.payment.line'
    _description = 'panexlogi.finance.payment.line'
    _inherit = ["mail.thread", "mail.activity.mixin"]

    payment_id = fields.Many2one('panexlogi.finance.payment', string='Payment')
    source = fields.Char(string='Source', tracking=True)
    source_code = fields.Char(string='Source Code', tracking=True)
    project = fields.Many2one('panexlogi.project', string='Project（项目）', tracking=True)
    invoiceno = fields.Char(string='Invoice No(发票号)', tracking=True)
    invoice_date = fields.Date(string='Invoice Date(发票日期)', tracking=True)
    due_date = fields.Date(string='Due Date(到期日)', tracking=True)
    fitem = fields.Many2one('panexlogi.fitems', string='Item(费用项目)', tracking=True)
    fitem_name = fields.Char(string='Item Name(费用项目名称)', related='fitem.name', readonly=True)
    pay_amount = fields.Float(string='Amount（欧元金额）', tracking=True)
    pay_amount_usd = fields.Float(string='Amount（美元金额）', tracking=True)
    pay_remark = fields.Text(string='Remark', tracking=True)
