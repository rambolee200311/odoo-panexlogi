from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
import requests
import logging
import base64

_logger = logging.getLogger(__name__)


class ARInvoice(models.Model):
    _name = 'panexlogi.ar.invoice'
    _description = 'panexlogi.ar.invoice'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = "billno"

    billno = fields.Char("Bill No", readonly=True)
    date = fields.Date(string="Date", default=fields.Date.context_today)

    ar_company = fields.Many2one('res.partner', string='Payee（收款方）',
                                 domain="[('is_company', '=', True),('category_id.name', 'ilike', 'company')]")
    ar_company_account = fields.Many2one('res.partner.bank', string='Payee Account',
                                            domain="[('partner_id', '=', ar_company)]")

    fiscal_year = fields.Many2one("fiscal.year", string="Fiscal Year")
    fiscal_month = fields.Many2one("fiscal.month", string="Fiscal Month")
    occurred_month = fields.Char(string="Occurred Month", required=True)
    project = fields.Many2one("panexlogi.project", string="Project")
    project_manager = fields.Many2one("res.users", string="Project Manager", default=lambda self: self.env.user)
    customer = fields.Many2one("res.partner", string="Customer",
                               domain="[('is_company', '=', True)]")
    remark = fields.Text(string="Remark")

    currency_id = fields.Many2one('res.currency', string='Currency（币种）', required=True, tracking=True,
                                  default=lambda self: self.env.ref('base.EUR'))
    invoice_amount = fields.Float(string="Invoice Amount", compute="_compute_amount", store=True)
    invoice_vat = fields.Float(string="Invoice VAT", compute="_compute_vat", store=True)
    invoice_amount_with_vat = fields.Float(string="Invoice Amount(with VAT)", compute="_compute_amount_with_vat",
                                           store=True)
    state = fields.Selection([('new', 'New'),
                              ('confirm', 'Confirm'),
                              ('cancel', 'Cancel'), ],
                             default='new', tracking=True)

    receive_amount = fields.Float(string="Receive Amount")
    invoice_amount_balance = fields.Float(string="Invoice Amount Balance", compute="_compute_invoice_amount_balance",
                                          store=True)

    invoice_pdf = fields.Binary(string="Invoice PDF")
    invoice_pdf_name = fields.Char(string="Invoice PDF Name")
    invoice_date = fields.Date(string="Invoice Date")
    invoice_due_date = fields.Date(string="Due Date")
    invoice_number = fields.Char(string="Invoice Number")

    invoice_line_ids = fields.One2many('panexlogi.ar.invoice.line', 'ar_invoice_id', string="Invoice Line")
    invoice_receive_details_ids = fields.One2many('panexlogi.ar.invoice.receive.details', 'invoice_id',
                                                  string="Receive Details")
    ar_bill_id = fields.Many2one('panexlogi.ar.bill', string='AR Bill')
    # Properly define company_id and exclude from tracking
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        tracking=False  # Explicitly disable tracking
    )

    #
    # def _mail_track_get_field_sequence(self, field_name):
    #     # Exclude 'company_id' from being tracked
    #     if field_name == 'company_id':
    #         return None
    #     return super()._mail_track_get_field_sequence(field_name)

    @api.depends('receive_amount', 'invoice_amount_with_vat')
    def _compute_invoice_amount_balance(self):
        for rec in self:
            rec.invoice_amount_balance = 0
            rec.invoice_amount_balance = rec.invoice_amount_with_vat - rec.receive_amount

    @api.onchange('project')
    def _onchange_project(self):
        if self.project:
            self.customer = self.project.customer

    @api.model
    def create(self, values):
        """
        generate bill number
        """
        times = fields.Date.today()
        values['billno'] = self.env['ir.sequence'].next_by_code('seq.ar.invoice', times)
        return super(ARInvoice, self).create(values)

    def action_confirm(self):
        for record in self:
            if record.state == 'new':
                record.state = 'confirm'
                if record.ar_bill_id:
                    record.ar_bill_id._compute_receive_amount()
                    record.ar_bill_id._compute_status()
                    # Send Odoo message
                    subject = 'A/R Invoice Confirmed'
                    # Get base URL
                    base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                    # Construct URL to the A/R Invoice
                    ar_invoice_url = "{}/web#id={}&model=panexlogi.ar.invoice&view_type=form".format(
                        base_url,
                        record.id
                    )
                    # HTML content
                    content = f'''
                        <p>Hello,</p>
                        <p>An A/R Invoice has been confirmed:</p>
                        <p><a href="{ar_invoice_url}" style="color: #1A73E8; text-decoration: none; font-weight: bold;">View A/R Invoice</a></p>
                        <p>Click the link above to access the details.</p>
                    '''
                    # Notify the creator of the AR Bill
                    creator_partner = record.ar_bill_id.create_uid.partner_id
                    if creator_partner:
                        # Add the creator as a follower
                        record.message_subscribe(partner_ids=[creator_partner.id])
                        # Send the notification
                        record.message_post(
                            body=content,
                            subject=subject,
                            message_type='notification',
                            subtype_xmlid="mail.mt_comment",  # Correct subtype for notifications
                            body_is_html=True,  # Render HTML in the email
                        )
            else:
                raise UserError("Only new invoices can be confirmed.")

    def action_renew(self):
        for record in self:
            if record.state == 'cancel':
                record.state = 'new'
            else:
                raise UserError("Only canceled invoices can be renewed.")

    def action_cancel(self):
        for record in self:
            if record.state == 'new':
                if record.ar_bill_id:
                    record.ar_bill_id.ar_invoice_id = False
                    record.ar_bill_id._compute_receive_amount()
                    record.ar_bill_id._compute_status()
                    # record.ar_bill_id.status = "billed"
                for line in record.invoice_line_ids:
                    line.ab_bill_id = False
                    line.ar_bill_line_id = False
                    ar_bill_line = self.env['panexlogi.ar.bill.line'].search([('ar_invoice_line_id', '=', line.id)])
                    if ar_bill_line:
                        ar_bill_line.ar_invoice_line_id = False
                record.state = 'cancel'
            else:
                '''
                for line in record.invoice_line_ids:
                    line.ab_bill_id = False
                    line.ar_bill_line_id = False
                    
                    ar_bill_line = self.env['panexlogi.ar.bill.line'].search([('ar_invoice_line_id', '=', line.id)])
                    if ar_bill_line:
                        ar_bill_line.ar_invoice_line_id = False
                        ar_bill_line.invoice_amount -= line.invoice_amount
                        ar_bill_line.invoice_vat -= line.invoice_vat
                        ar_bill_line.invoice_amount_with_vat -= line.invoice_amount_with_vat
                '''

                raise UserError("Only new invoices can be canceled.")

    def action_unconfirm(self):
        for record in self:
            if record.state == 'confirm':
                if record.invoice_receive_details_ids:
                    raise UserError("Cannot unconfirm invoice with receive details.")

                record.state = 'new'
                if record.ar_bill_id:
                    record.ar_bill_id._compute_receive_amount()
                    record.ar_bill_id._compute_status()
            else:
                raise UserError("Only confirmed bills can be unconfirmed.")

    @api.depends('invoice_receive_details_ids')
    def _compute_receive_amount(self):
        for record in self:
            total_amount = 0.0
            for line in record.invoice_receive_details_ids:
                total_amount += line.receive_amount
            record.receive_amount = total_amount
            if record.ar_bill_id:
                record.ar_bill_id._compute_receive_amount()
                record.ar_bill_id._compute_status()

    @api.depends('invoice_line_ids.invoice_amount')
    def _compute_amount(self):
        for record in self:
            total_amount = 0.0
            for line in record.invoice_line_ids:
                total_amount += line.invoice_amount
            record.invoice_amount = total_amount

    @api.depends('invoice_line_ids.invoice_vat')
    def _compute_vat(self):
        for record in self:
            total_vat = 0.0
            for line in record.invoice_line_ids:
                total_vat += line.invoice_vat
            record.invoice_vat = total_vat

    @api.depends('invoice_amount', 'invoice_vat')
    def _compute_amount_with_vat(self):
        for record in self:
            record.invoice_amount_with_vat = record.invoice_amount + record.invoice_vat

    @api.depends('invoice_receive_details_ids.receive_amount')
    def _compute_receive_amount(self):
        for record in self:
            for line in record.invoice_receive_details_ids:
                record.receive_amount += line.receive_amount

    def action_print_pdf(self):
        from odoo import _
        """Generate and store the invoice PDF with error handling and performance optimization"""
        self.ensure_one()
        try:
            for rec in self:
                # Clear existing PDF
                rec.write({
                    'invoice_pdf': False,
                    'invoice_pdf_name': False
                })
                # Get predefined report reference
                report = self.env['ir.actions.report'].search([
                    ('report_name', '=', 'panexLogi.report_ar_invoice_template_view')
                ], limit=1)

                # Force template reload and generate PDF
                self.env.flush_all()

                # Use standard rendering method
                result = report._render_qweb_pdf(report_ref=report.report_name,
                                                 res_ids=[rec.id],
                                                 data=None)

                # Validate return structure
                if not isinstance(result, tuple) or len(result) < 1:
                    raise ValueError("Invalid data structure returned from report rendering")

                pdf_content = result[0]

                # Create attachment
                invoice_file = self.env['ir.attachment'].create({
                    'name': f'AR_Invoice_{self.billno}_{fields.Datetime.now().strftime("%Y%m%d%H%M%S")}.pdf',
                    'type': 'binary',
                    'datas': base64.b64encode(pdf_content),
                    'res_model': self._name,
                    'res_id': rec.id,
                })

                # Batch write with sudo
                rec.sudo().write({
                    'invoice_pdf': invoice_file.datas,
                    'invoice_pdf_name': invoice_file.name
                })

        except Exception as e:
            error_msg = f"PDF Generation Failed: {str(e)}"
            _logger.error(error_msg)
            raise UserError(_(f"{error_msg}\nCheck server logs (ID:{self.id})")) from e


class ARInvoiceLine(models.Model):
    _name = 'panexlogi.ar.invoice.line'
    _description = 'panexlogi.ar.invoice.line'

    fitem = fields.Many2one('panexlogi.fitems', string='Item(费用项目)', tracking=True)
    fitem_name = fields.Char(string='Item Name(费用项目名称)', related='fitem.name', readonly=True)

    remark = fields.Text(string="Remark")

    invoice_amount = fields.Float(string="Invoice Amount")
    invoice_vat = fields.Float(string="Invoice VAT")
    invoice_amount_with_vat = fields.Float(string="Invoice Amount(with VAT)", compute="_compute_amount_with_vat",
                                           store=True)

    receive_amount = fields.Float(string="Receive Amount")

    ar_invoice_id = fields.Many2one('panexlogi.ar.invoice', string='AR Bill', ondelete='cascade')
    ab_bill_id = fields.Many2one('panexlogi.ar.bill', string='AR Bill')
    ar_bill_line_id = fields.Many2one('panexlogi.ar.bill.line', string='AR Bill Line')

    @api.depends('invoice_amount', 'invoice_vat')
    def _compute_amount_with_vat(self):
        for record in self:
            record.invoice_amount_with_vat = 0
            record.invoice_amount_with_vat = record.invoice_amount + record.invoice_vat


class ARInvoiceReceiveDetails(models.Model):
    _name = 'panexlogi.ar.invoice.receive.details'
    _description = 'panexlogi.ar.invoice.receive.details'

    invoice_id = fields.Many2one('panexlogi.ar.invoice', string='AR Invoice')
    ar_receive_id = fields.Many2one('panexlogi.ar.receive', string='AR Receive')

    receive_amount = fields.Float(string="Receive Amount")
    receive_date = fields.Date(string="Receive Date")
    remark = fields.Text(string="Remark")
