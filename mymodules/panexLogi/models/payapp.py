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
    pdffile = fields.Binary(string='Invoice File（原件）')
    pdffilename = fields.Char(string='File name')
    total_amount = fields.Float(string='Amount（欧元金额）', compute='_compute_amount', tracking=True,
                                store=True)
    total_amount_usd = fields.Float(string='Amount（美元金额）', compute='_compute_amount', tracking=True,
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
    source = fields.Char(string='Source', readonly=True)
    source_Code = fields.Char(string='Source Code', readonly=True)
    invoiceno = fields.Char(string='Invoice No(发票号)', readonly=True)
    invoice_date = fields.Date(string='Invoice Date(发票日期)', readonly=True)
    due_date = fields.Date(string='Due Date(到期日)', readonly=True)

    pay_date = fields.Date(string='Pay Date(付款日期)', tracking=True)
    pay_amount = fields.Float(string='Pay Amount（欧元金额）', tracking=True)
    pay_amount_usd = fields.Float(string='Pay Amount（美元金额）', tracking=True)
    pay_remark = fields.Text(string='Pay Remark', tracking=True)
    pay_pdffile = fields.Binary(string='Pay File（原件）')
    pay_pdffilename = fields.Char(string='Pay File name')
    payment_id = fields.Many2one('panexlogi.finance.payment', string='Payment')

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
            rec.total_amount_usd = 0
            if rec.paymentapplicationline_ids:
                rec.total_amount = sum(rec.paymentapplicationline_ids.mapped('amount'))
                rec.total_amount_usd = sum(rec.paymentapplicationline_ids.mapped('amount_usd'))

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
            if rec.payment_id:
                payment = self.env['panexlogi.finance.payment'].search(
                    [('id', '=', rec.payment_id.id), ('state', '!=', 'cancel')])
                if payment:
                    raise UserError(_("You can't unconfirm paid application"))
            rec.payment_id = False
            rec.state = 'new'
            return True

    def action_cancel_order(self):
        for rec in self:
            if rec.state != 'new':
                raise UserError(_("You only can cancel New application"))
            if rec.payment_id:
                raise UserError(_("You can't cancel paid application"))

            # change shipping invoice state
            if rec.source == 'Shipping Invoice' and rec.type == 'import':
                shipinvoice = self.env['panexlogi.waybill.shipinvoice'].search([('billno', '=', rec.source_Code)])
                if shipinvoice:
                    shipinvoice.state = 'confirm'
                else:
                    raise exceptions.ValidationError('Can not find the Shipping Invoice')
            # change clearance invoice state
            if rec.source == 'Clearance Invoice' and rec.type == 'import':
                clearanceinvoice = self.env['panexlogi.waybill.clearinvoice'].search([('billno', '=', rec.source_Code)])
                if clearanceinvoice:
                    clearanceinvoice.state = 'confirm'
                else:
                    raise exceptions.ValidationError('Can not find the Clearance Invoice')

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
    """
            定时任务，每天更新状态为paid的付款申请
    """

    def cron_update_state_paid(self):
        for rec in self.search([('state', '=', 'confirm')]):
            source = rec.type,
            souce_code = rec.billno
            domain = [('source', '=', source), ('source_code', '=', souce_code), ('payment_id.state', '=', 'paid')]
            payment = self.env['panexlogi.finance.payment.line'].search(domain)
            if payment:
                rec.state = 'paid'
                if rec.source == 'Shipping Invoice' and rec.type == 'import':
                    shipinvoice = self.env['panexlogi.waybill.shipinvoice'].search(
                        [('billno', '=', rec.source_Code),
                         ('state', '=', 'apply')])
                    if shipinvoice:
                        shipinvoice.state = 'paid'
                if rec.source == 'Clearance Invoice' and rec.type == 'import':
                    clearanceinvoice = self.env['panexlogi.waybill.clearinvoice'].search(
                        [('billno', '=', rec.source_Code)
                            , ('state', '=', 'apply')])
                    if clearanceinvoice:
                        clearanceinvoice.state = 'paid'
                if rec.source == 'Transport Invoice' and rec.type == 'trucking':
                    transportinvoice = self.env['panexlogi.transport.invoice'].search(
                        [('billno', '=', rec.source_Code),
                         ('state', '=', 'apply')])
                    if transportinvoice:
                        transportinvoice.state = 'paid'
                if rec.source == 'Delivery Invoice' and rec.type == 'trucking':
                    deliveryinvoice = self.env['panexlogi.delivery.invoice'].search(
                        [('billno', '=', rec.source_Code),
                         ('state', '=', 'apply')])
                    if deliveryinvoice:
                        deliveryinvoice.state = 'paid'

                        # select multi rows create a paymentcd

    def action_create_payment_from_selected(self):
        selected_applications = self.browse(self.env.context.get('active_ids'))

        # Ensure at least one record is selected
        if not selected_applications:
            raise UserError("Please select at least one payment application.")
        payee = selected_applications[0].payee
        state = selected_applications[0].state
        # Ensure all in confirm state
        if state != 'confirm':
            raise UserError("Please select the confirm state.")
        for application in selected_applications:
            if not application.paymentapplicationline_ids:
                raise UserError("Please check selected payment whether have at least on line.")
            # Ensure select records are in the same payee and in the same state
            if application.payee != payee:
                raise UserError("Please select the same payee.")
            if application.state != state:
                raise UserError("Please select the same state.")
            # Ensure select record not create payment
            type = 'payment'
            source = application.type,
            souce_code = application.billno
            domain = [('source', '=', source), ('source_code', '=', souce_code), ('payment_id.state', '!=', 'cancel')]
            payment = self.env['panexlogi.finance.payment.line'].search(domain)
            if payment:
                raise UserError("Please select the record which had not created payment.")

        # Create a new payment (you can customize this logic as needed)
        panex_partner = self.env['res.partner.bank'].search([('partner_id', '=', payee.id)], limit=1)
        # Initialize with empty strings to avoid KeyErrors
        bankid = panex_partner.id if panex_partner else 0

        new_payment = self.env['panexlogi.finance.payment'].create({
            'type': 'payment',  # Example: Outbound payment
            'payee': payee.id,
            'payee_account_partner': bankid,
            'pay_date': fields.Date.today(),
        })
        for application in selected_applications:
            # Create payment lines for each selected record
            for rec in application.paymentapplicationline_ids:
                self.env['panexlogi.finance.payment.line'].create({
                    'payment_id': new_payment.id,
                    'source': application.type,
                    'source_code': application.billno,
                    'project': rec.project.id,
                    'fitem': rec.fitem.id,
                    'pay_amount': rec.amount,
                    'pay_amount_usd': rec.amount_usd,
                    'invoice_date': application.invoice_date,
                    'due_date': application.due_date,
                    'invoiceno': application.invoiceno,
                    'pay_remark': rec.remark,
                })
            # Update the payment application with the new payment
            application.payment_id = new_payment.id

        # Open the newly created Payment form
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'panexlogi.finance.payment',
            'res_id': new_payment.id,
            'view_mode': 'form',
            'target': 'current',
        }


# 付款申请明细
class PaymentApplicationLine(models.Model):
    _name = 'panexlogi.finance.paymentapplicationline'
    _description = 'panexlogi.finance.paymentapplicationline'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = 'billno'

    billno = fields.Char(string='Code', readonly=True)
    project = fields.Many2one('panexlogi.project', string='Project（项目）', tracking=True)
    invoiceno = fields.Char(string='Invoice No(发票号)', tracking=True)
    invoice_date = fields.Date(string='Invoice Date(发票日期)', tracking=True)
    due_date = fields.Date(string='Due Date(到期日)', tracking=True)
    fitem = fields.Many2one('panexlogi.fitems', string='Item(费用项目)', tracking=True)
    fitem_name = fields.Char(string='Item Name(费用项目名称)', related='fitem.name', readonly=True)
    payapp_billno = fields.Many2one('panexlogi.finance.paymentapplication', tracking=True)
    amount = fields.Float(string='Amount（欧元金额）', tracking=True)
    amount_usd = fields.Float(string='Amount（美元金额）', tracking=True)
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

    waybill_billno = fields.Many2one('panexlogi.waybill', readonly=True)


# 卡车付款申请
class CartagePaymentApplicationLine(models.Model):
    _inherit = 'panexlogi.finance.paymentapplicationline'

    cartagebillno = fields.Many2one('panexlogi.cartage', readonly=True)
