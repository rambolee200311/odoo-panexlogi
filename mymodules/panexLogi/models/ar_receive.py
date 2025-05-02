from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
import requests
import logging

_logger = logging.getLogger(__name__)


# 收款单
class Receive(models.Model):
    _name = 'panexlogi.ar.receive'
    _description = 'panexlogi.ar.receive'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = 'billno'

    billno = fields.Char(string='Code', readonly=True)
    type = fields.Char(string='Type', readonly=True, default='Import')
    payer = fields.Many2one('res.partner', string='Payer（付款方）',
                            required=True, tracking=True, readonly=True)
    # payee_bank =fields.Char(string='Bank（收款方银行）', tracking=True)
    payer_account = fields.Char(string='Account（付款方账号）', tracking=True)
    payer_account_partner = fields.Many2one('res.partner.bank', string='Account（付款方账号）', tracking=True,
                                            domain="[('partner_id', '=', payer)]")
    payer_account_number = fields.Char(string='IBAN（付款方账号IBAN）', related='payer_account_partner.acc_number',
                                       readonly=True)
    payer_bank_bic = fields.Char(string='Bank BIC（付款方银行BIC）', related='payer_account_partner.bank_bic',
                                 readonly=True)

    payee = fields.Char(string='Payer（收款方）', tracking=True)
    payee_company = fields.Many2one('res.partner', string='Payee（收款方）', tracking=True,
                                    domain="[('is_company', '=', True),('category_id.name', 'ilike', 'company')]")
    payee_company_account = fields.Many2one('res.partner.bank', string='Account（收款方账号）', tracking=True,
                                            domain="[('partner_id', '=', payee_company)]")
    payee_bank = fields.Char(string='Bank（收款方银行）', related='payee_company_account.bank_bic', tracking=True)
    currency_id = fields.Many2one('res.currency', string='Currency（币种）', required=True, tracking=True,
                                  default=lambda self: self.env.ref('base.EUR'))
    payee_account = fields.Char(string='Account（收款方账号）', related='payee_company_account.acc_number', tracking=True)
    payment_method = fields.Many2one('panexlogi.finance.payment.method',
                                     string='Payment Method（收款方式）',
                                     domain=[('state', '=', 'active')], tracking=True)
    receive_date = fields.Date(string='Date(收款日期)', tracking=True)
    receive_amount = fields.Float(string='Amount（金额）', tracking=True, default=0)
    remark = fields.Text(string='Remark', tracking=True)
    pdffile = fields.Binary(string='File（原件）')
    pdffilename = fields.Char(string='File name')

    state = fields.Selection([('new', 'New'),
                              ('confirm', 'Confirm'),
                              ('cancel', 'Cancel'), ],
                             default='new')
    ar_receive_line_ids = fields.One2many('panexlogi.ar.receive.line', 'receive_id', string='Receive Line')
    invoice_number = fields.Char(string="Invoice Number")
    cost = fields.Float(string="Cost", default=0)

    global_total_receive_amount = fields.Float(
        string="Global Total Receive Amount",
        compute='_compute_global_total',
        store=False
    )
    global_total_cost = fields.Float(
        string="Global Total Cost",
        compute='_compute_global_total',
        store=False
    )

    @api.depends('receive_amount', 'cost')
    def _compute_global_total(self):
        all_records = self.search([])
        self.global_total_receive_amount = sum(all_records.mapped('receive_amount'))
        self.global_total_cost = sum(all_records.mapped('cost'))

    @api.model
    def create(self, values):
        """
        generate bill number
        """
        times = fields.Date.today()
        # if 'receive_amount' in values:
        #    values['receive_amount'] = self._convert_european_format(values['receive_amount'])
        values['billno'] = self.env['ir.sequence'].next_by_code('seq.ar.receive', times)
        return super(Receive, self).create(values)

    @api.model
    def write(self, values):
        # if 'receive_amount' in values:
        #    values['receive_amount'] = self._convert_european_format(values['receive_amount'])
        return super(Receive, self).write(values)

    # @api.onchange('receive_amount')
    # def _onchange_receive_amount(self):
    #    if isinstance(self.receive_amount, str):
    #        self.receive_amount = self._convert_european_format(self.receive_amount)

    def action_cancel(self):
        for rec in self:
            if rec.state == 'new':
                rec.state = 'cancel'
            else:
                raise UserError("The state of the record is not new, cannot be cancelled.")

    @staticmethod
    def _convert_european_format(value):
        if isinstance(value, str):
            # Remove all commas except the last one
            parts = value.split(',')
            length = len(parts)
            if length > 1:
                value = ''.join(parts[:-1]) + '.' + parts[-1]
            else:
                value = parts[0]
        try:
            return float(value)
        except ValueError:
            raise ValidationError("Invalid European number format for 'receive_amount'.")

    def action_confirm(self):
        for rec in self:
            if rec.state == 'new':
                # Check if receive_amount matches the sum of line amounts
                total_line_amount = sum(line.amount for line in rec.ar_receive_line_ids)
                if rec.receive_amount + rec.cost != total_line_amount:
                    raise ValidationError("The total of line amounts must equal the receive amount plus cost.")
                # Check if the invoice is not already fully paid
                if not rec.ar_receive_line_ids:
                    raise ValidationError("Please add at least one line to the receive.")

                for line in rec.ar_receive_line_ids:
                    # Create a new record in panexlogi.ar.invoice.receive.details
                    self.env['panexlogi.ar.invoice.receive.details'].create({
                        'invoice_id': line.ar_invoice_id.id,
                        'ar_receive_id': rec.id,
                        'receive_amount': line.amount,
                        'receive_date': rec.receive_date,
                        'remark': line.remark,
                    })
                    # Update the receive_amount in the invoice
                    line.ar_invoice_id.receive_amount += line.amount
                    if line.ar_invoice_id.ar_bill_id:
                        line.ar_invoice_id.ar_bill_id._compute_receive_amount()
                        line.ar_invoice_id.ar_bill_id._compute_status()
                rec.state = 'confirm'

            else:
                raise UserError("The state of the record is not new, cannot be confirmed.")

    def action_unconfirm(self):
        for rec in self:
            if rec.state == 'confirm':
                for line in rec.ar_receive_line_ids:
                    # Find and delete related receive details
                    details = self.env['panexlogi.ar.invoice.receive.details'].search([
                        ('invoice_id', '=', line.ar_invoice_id.id),
                        ('ar_receive_id', '=', rec.id),
                    ])
                    details.unlink()
                    # Adjust the receive_amount in the invoice
                    line.ar_invoice_id.receive_amount -= line.amount
                    if line.ar_invoice_id.ar_bill_id:
                        line.ar_invoice_id.ar_bill_id._compute_receive_amount()
                        line.ar_invoice_id.ar_bill_id._compute_status()
                rec.state = 'new'
            else:
                raise UserError("The state of the record is not confirm, cannot be unconfirmed.")

    def action_renew(self):
        for rec in self:
            if rec.state == 'cancel':
                rec.state = 'new'
            else:
                raise UserError("The state of the record is not cancel, cannot be renewed.")


class ReceiveLine(models.Model):
    _name = 'panexlogi.ar.receive.line'
    _description = 'panexlogi.ar.receive.line'
    _rec_name = 'ar_invoice_id'

    ar_invoice_id = fields.Many2one('panexlogi.ar.invoice', string='AR Invoice',
                                    domain="[('state', '=', 'confirm'), ('invoice_amount_with_vat', '>', receive_amount)]")
    invoice_date = fields.Date(string='Invoice Date', related='ar_invoice_id.invoice_date')
    invoice_due_date = fields.Date(string='Invoice Due Date', related='ar_invoice_id.invoice_due_date')
    invoice_number = fields.Char(string='Invoice Number', related='ar_invoice_id.invoice_number')
    invoice_amount_with_vat = fields.Float(string='Invoice Amount', related='ar_invoice_id.invoice_amount_with_vat')
    receive_amount = fields.Float(string='Receive Amount', related='ar_invoice_id.receive_amount')
    invoice_amount_balance = fields.Float(string='Invoice Amount Balance',
                                          related='ar_invoice_id.invoice_amount_balance')
    amount = fields.Float(string='Amount')
    remark = fields.Text(string='Remark')

    receive_id = fields.Many2one('panexlogi.ar.receive', string='AR Receive')

    @api.onchange('amount')
    def _onchange_amount(self):
        for rec in self:
            if rec.amount > rec.invoice_amount_with_vat - rec.receive_amount:
                raise ValidationError("The amount cannot be greater than the invoice balance.")

    @api.constrains('amount')
    def _check_amount(self):
        for rec in self:
            if rec.amount == 0:
                raise ValidationError("The amount cannot equal 0.")
            if rec.amount > rec.invoice_amount_with_vat - rec.receive_amount:
                raise ValidationError("The amount cannot be greater than the invoice balance.")
