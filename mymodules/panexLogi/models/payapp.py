import logging

from odoo import _, models, fields, api, exceptions
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


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

    pay_date = fields.Date(string='Pay Date(付款日期)',
                           tracking=True,
                           store=True,
                           compute='computer_payment_id')
    pay_amount = fields.Float(string='Pay Amount（欧元金额）',
                              tracking=True,
                              store=True,
                              compute='computer_payment_id')
    pay_amount_usd = fields.Float(string='Pay Amount（美元金额）',
                                  tracking=True,
                                  store=True,
                                  compute='computer_payment_id')
    pay_remark = fields.Text(string='Pay Remark',
                             tracking=True,
                             store=True,
                             compute='computer_payment_id')
    pay_pdffile = fields.Binary(string='Pay File（原件）')
    pay_pdffilename = fields.Char(string='Pay File name')
    payment_id = fields.Many2one('panexlogi.finance.payment', string='Payment')
    shipinvoice_id = fields.Many2one('panexlogi.waybill.shipinvoice', 'Invoice ID')
    clearinvoice_id = fields.Many2one('panexlogi.waybill.clearinvoice', 'Invoice ID')
    trasportinvoice_id = fields.Many2one('panexlogi.transport.invoice', 'Invoice ID')
    '''
    @api.depends('payment_id')
    def computer_payment_id(self):
        for record in self:
            if record.payment_id:
                for line in record.payment_id.paymentline_ids:
                    if line.source == record.type and line.source_code == record.billno and record.payment_id.state == 'paid':
                        record.pay_date = line.pay_date
                        record.pay_amount = line.pay_amount
                        record.pay_amount_usd = line.pay_amount_usd
                        record.pay_remark = line.pay_remark
                        break  # Exit the loop once a match is found
            else:
                # Reset fields if no payment_id is found
                record.pay_date = False
                record.pay_amount = 0.0
                record.pay_amount_usd = 0.0
                record.pay_remark = False
    '''
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

    # monitor state change
    def write(self, vals):
        previous_states = {}
        # 捕获变更前的状态
        if 'state' in vals:
            previous_states = {rec.id: rec.state for rec in self}

        # 执行原始写入操作
        result = super(PaymentApplication, self).write(vals)

        # 状态变更后逻辑
        if 'state' in vals:
            for record in self:
                previous_state = previous_states.get(record.id, '')
                new_state = vals.get('state', '')

                # 仅在状态从 'confirm' 变更时触发
                if previous_state == 'confirm' and new_state != 'confirm':
                    record.message_post(
                        subject='Payment State Change',
                        body=f"state : '{previous_state}' --> '{new_state}'",
                        message_type='notification',
                        subtype_xmlid="mail.mt_comment",  # Correct subtype for emails
                        body_is_html=True,  # Render HTML in email
                        force_send=True,
                    )
        return result

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
            if rec.source == 'Shipping Invoice':
                shipinvoice = self.env['panexlogi.waybill.shipinvoice'].search([('billno', '=', rec.source_Code)])
                if shipinvoice:
                    shipinvoice.state = 'confirm'
                else:
                    raise exceptions.ValidationError('Can not find the Shipping Invoice')
            # change clearance invoice state
            if rec.source == 'Clearance Invoice':
                clearanceinvoice = self.env['panexlogi.waybill.clearinvoice'].search([('billno', '=', rec.source_Code)])
                if clearanceinvoice:
                    clearanceinvoice.state = 'confirm'
                else:
                    raise exceptions.ValidationError('Can not find the Clearance Invoice')
            # change transport invoice state
            if rec.source == 'Transport Invoice':
                transportinvoice = self.env['panexlogi.transport.invoice'].search([('billno', '=', rec.source_Code)])
                if transportinvoice:
                    transportinvoice.state = 'confirm'
                else:
                    raise exceptions.ValidationError('Can not find the Transport Invoice')
            # change delivery invoice state
            if rec.source == 'Delivery Invoice':
                deliveryinvoice = self.env['panexlogi.delivery.invoice'].search([('billno', '=', rec.source_Code)])
                if deliveryinvoice:
                    deliveryinvoice.state = 'confirm'
                else:
                    raise exceptions.ValidationError('Can not find the Delivery Invoice')
            # change warehouse invoice state
            if rec.source == 'Warehouse Invoice':
                warehouseinvoice = self.env['panexlogi.warehouse.invoice'].search([('billno', '=', rec.source_Code)])
                if warehouseinvoice:
                    warehouseinvoice.state = 'confirm'
                else:
                    raise exceptions.ValidationError('Can not find the Warehouse Invoice')
            if rec.source == 'A/R Bill':
                ar_bill = self.env['panexlogi.ar.bill'].search([('billno', '=', rec.source_Code)])
                if ar_bill:
                    ar_bill.state = 'confirm'
                    ar_bill.payment_application_id = False

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
        for rec in self.search([('state', 'in', ['confirm', 'paid'])]):
            try:
                source = rec.type
                source_code = rec.billno

                domain = [('source', '=', source), ('source_code', '=', source_code), ('payment_id.state', '=', 'paid')]
                payment = self.env['panexlogi.finance.payment.line'].search(domain)

                if rec.state == 'confirm' and payment:
                    state_time = fields.Datetime.now()
                    payapp_billno = rec.billno
                    _logger.info("%s : cron_update_state_paid started at: %s", payapp_billno, state_time)

                    rec.state = 'paid'

                    # Update related invoices based on the source and type
                    if rec.source == 'Shipping Invoice' and rec.type == 'import':
                        shipinvoice = self.env['panexlogi.waybill.shipinvoice'].search(
                            [('billno', '=', rec.source_Code), ('state', '=', 'apply')]
                        )
                        if shipinvoice:
                            shipinvoice.state = 'paid'

                    elif rec.source == 'Clearance Invoice' and rec.type == 'import':
                        clearanceinvoice = self.env['panexlogi.waybill.clearinvoice'].search(
                            [('billno', '=', rec.source_Code), ('state', '=', 'apply')]
                        )
                        if clearanceinvoice:
                            clearanceinvoice.state = 'paid'

                    elif rec.source == 'Transport Invoice' and rec.type == 'trucking':
                        transportinvoice = self.env['panexlogi.transport.invoice'].search(
                            [('billno', '=', rec.source_Code), ('state', '=', 'apply')]
                        )
                        if transportinvoice:
                            transportinvoice.state = 'paid'

                    elif rec.source == 'Delivery Invoice' and rec.type == 'trucking':
                        deliveryinvoice = self.env['panexlogi.delivery.invoice'].search(
                            [('billno', '=', rec.source_Code), ('state', '=', 'apply')]
                        )
                        if deliveryinvoice:
                            deliveryinvoice.state = 'paid'

                    # Log and notify administrators
                    end_time = fields.Datetime.now()
                    _logger.info("%s : cron_update_state_paid ended at: %s", payapp_billno, end_time)
                    rec.message_post(
                        body='Update state to paid, start time: %s, end time: %s, payapp_billno: %s'
                             % (state_time, end_time, payapp_billno),
                        partner_ids=self.env['res.users'].search([('groups_id.name', '=', 'Administrator')]).mapped(
                            "partner_id").ids,
                        subject='Update state to paid',
                        message_type='notification',
                        subtype_xmlid="mail.mt_comment",
                        body_is_html=True,
                        force_send=True,
                    )

                elif rec.state == 'paid' and payment:
                    # Update payment details for already paid records
                    rec.pay_date = payment.payment_id.pay_date
                    rec.pay_amount = payment.pay_amount
                    rec.pay_amount_usd = payment.pay_amount_usd
                    rec.pay_remark = payment.pay_remark

            except Exception as e:
                _logger.error(f"Error in updating payment details for {rec.billno}: {str(e)}")
                continue

        return  # Explicitly return None

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

    # link to parent payment application
    parent_billno = fields.Char(related="payapp_billno.billno", string="Bill No", readonly=True)
    parent_type = fields.Char(related="payapp_billno.type", string="Type", readonly=True)
    parent_date = fields.Date(related="payapp_billno.date", string="Date", readonly=True)
    parent_payee = fields.Many2one(related="payapp_billno.payee", string="Payee", readonly=True)
    parent_state = fields.Selection(related="payapp_billno.state", string="State", readonly=True)
    parent_source = fields.Char(related="payapp_billno.source", string="Source", readonly=True)
    parent_source_code = fields.Char(
        related="payapp_billno.source_Code",
        string="Source Code",
        readonly=True
    )
    parent_pay_date = fields.Date(related="payapp_billno.pay_date", string="Pay Date", readonly=True)
    parent_pay_amount = fields.Float(related="payapp_billno.pay_amount", string="Pay Amount", readonly=True)
    parent_remark = fields.Text(
        related="payapp_billno.remark",
        string="Parent Remark",
        readonly=False,
    )
    created_by = fields.Many2one(
        related="payapp_billno.create_uid",
        string="Created By",
        readonly=True
    )
    parent_invoiceno = fields.Char(string='Invoice No', related="payapp_billno.invoiceno", readonly=True)
    parent_invoice_date = fields.Date(string='Invoice Date', related="payapp_billno.invoice_date", readonly=True)
    parent_due_date = fields.Date(string='Due Date', related="payapp_billno.due_date", readonly=True)

    @api.model
    def create(self, values):
        """
        生成跟踪单号
        """
        times = fields.Date.today()
        values['billno'] = self.env['ir.sequence'].next_by_code('seq.finance.paymentapplicationline', times)

        return super(PaymentApplicationLine, self).create(values)

    # @api.model
    def cron_update_project(self):
        """
        Scheduled task to update the project field for payment application lines.
        """
        try:
            _logger.info("Starting cron_update_project")
            for rec in self.env['panexlogi.finance.paymentapplicationline'].search([('project', '=', False)]):
                _logger.info(f"Project {rec.project.project_name} for BillNo: {rec.payapp_billno.billno}")
                if not rec.project:
                    # Check if the project is linked via the waybill
                    _logger.info(f"Updating project for billno: {rec.payapp_billno.billno}")
                    if rec.payapp_billno.waybill_billno and rec.payapp_billno.waybill_billno.project:
                        rec.project = rec.payapp_billno.waybill_billno.project.id
                        continue

                    # Handle different sources
                    source_mapping = {
                        'Shipping Invoice': 'panexlogi.waybill.shipinvoice',
                        'Clearance Invoice': 'panexlogi.waybill.clearinvoice',
                        'Warehouse Invoice': 'panexlogi.warehouse.invoice',
                        'Transport Invoice': 'panexlogi.transport.invoice',
                        'Delivery Invoice': 'panexlogi.delivery.invoice',
                    }

                    model_name = source_mapping.get(rec.payapp_billno.source)
                    if model_name:
                        invoice = self.env[model_name].search([('billno', '=', rec.payapp_billno.source_Code)], limit=1)
                        if invoice:
                            if rec.payapp_billno.source == 'Transport Invoice':
                                for detail in invoice.transportinvoicedetailids:
                                    waybill = self.env['panexlogi.waybill'].search(
                                        [('waybillno', '=', detail.waybillno)], limit=1)
                                    if waybill:
                                        rec.project = waybill.project.id
                                        break
                            elif rec.payapp_billno.source == 'Delivery Invoice':
                                for detail in invoice.deliveryinvoicedetailids:
                                    inner_ref_parts = detail.inner_ref.split('-')
                                    domain = [('deliveryid.trucker', '=', rec.payapp_billno.payee.id),
                                              ('deliveryid.state', '!=', 'cancel')]
                                    domain += ['|'] * (len(inner_ref_parts) - 1)
                                    domain += [('|', ('loading_ref', 'ilike', part), ('cntrno', 'ilike', part)) for part
                                               in inner_ref_parts]
                                    delivery_detail = self.env['panexlogi.delivery.detail'].search(domain, limit=1)
                                    if delivery_detail:
                                        rec.project = delivery_detail.deliveryid.project.id
                                        break
                            else:
                                rec.project = invoice.project.id
                        else:
                            _logger.warning(
                                f"No matching record found for source: {rec.payapp_billno.source}, Code: {rec.payapp_billno.source_Code}")
                    else:
                        _logger.warning(f"Unsupported source type: {rec.payapp_billno.source}")
                else:
                    _logger.info(f"Project already set for record ID: {rec.id}")
        except Exception as e:
            _logger.error(f"Error in cron_update_project: {str(e)}")
        return True


# 进口付款申请
class ImportPaymentApplication(models.Model):
    _inherit = 'panexlogi.finance.paymentapplication'

    waybill_billno = fields.Many2one('panexlogi.waybill', readonly=True)


# 卡车付款申请
class CartagePaymentApplicationLine(models.Model):
    _inherit = 'panexlogi.finance.paymentapplicationline'

    cartagebillno = fields.Many2one('panexlogi.cartage', readonly=True)
