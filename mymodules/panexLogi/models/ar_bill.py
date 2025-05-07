from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
import requests
import logging

_logger = logging.getLogger(__name__)


class ARBill(models.Model):
    _name = 'panexlogi.ar.bill'
    _description = 'panexlogi.ar.bill'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = "billno"

    billno = fields.Char("Bill No", readonly=True)
    date = fields.Date(string="Date", default=fields.Date.context_today)
    fiscal_year = fields.Many2one("fiscal.year", string="Fiscal Year", required=True)
    fiscal_month = fields.Many2one("fiscal.month", string="Fiscal Month", required=True)
    occurred_month = fields.Char(string="Occurred Month", required=True)
    project = fields.Many2one("panexlogi.project", string="Project")
    project_manager = fields.Many2one("res.users", string="Project Manager", default=lambda self: self.env.user)
    customer = fields.Many2one("res.partner", string="Customer",
                               domain="[('is_company', '=', True), ('project', '=', True)]")
    remark = fields.Text(string="Remark")
    amount = fields.Float(string="Amount", compute="_compute_amount", store=True)
    vat = fields.Float(string="VAT", compute="_compute_vat", store=True)
    amount_with_vat = fields.Float(string="Amount(with VAT)", compute="_compute_amount_with_vat", store=True)
    state = fields.Selection([('new', 'New'),
                              ('confirm', 'Confirm'),
                              ('cancel', 'Cancel'), ],
                             default='new', tracking=True)
    status = fields.Selection([('billed', 'Billed'),
                               ('invoiced', 'Invoiced'),
                               ('received', 'Received'),
                               ('full received', 'Fully Received'),
                               ('part received', 'Partly Received'),
                               ('other', 'Other'), ], compute='_compute_status', store=True,
                              default='billed')
    bill_line_ids = fields.One2many('panexlogi.ar.bill.line', 'ar_bill_id', string="Bill Line")
    bill_doc_ids = fields.One2many('panexlogi.ar.bill.doc', 'ar_bill_id', string="Bill Document")
    currency_id = fields.Many2one('res.currency', string='Currency（币种）', required=True, tracking=True,
                                  default=lambda self: self.env.ref('base.EUR'))
    invoice_amount = fields.Float(string="Invoice Amount", compute="_compute_receive_amount", store=True)
    invoice_vat = fields.Float(string="Invoice VAT", compute="_compute_receive_amount", store=True)
    invoice_amount_with_vat = fields.Float(string="Invoice Amount(with VAT)", compute="_compute_receive_amount",
                                           store=True)

    receive_amount = fields.Float(string="Receive Amount", compute="_compute_receive_amount", store=True)

    ar_invoice_id = fields.Many2one('panexlogi.ar.invoice', string='AR Invoice', readonly=True)
    original_ar_bill_id = fields.Many2one('panexlogi.ar.bill', string='Original AR Bill', readonly=True)
    credit_note_ar_bill_id = fields.Many2one('panexlogi.ar.bill', string='Credit Note AR Bill', readonly=True)

    @api.returns('self', lambda value: value.id if value else None)
    def copy(self, default=None):
        """Override copy to generate new bill number for all duplicates"""
        default = dict(default or {})
        default.update({
            'billno': self.env['ir.sequence'].next_by_code('seq.ar.bill'),
            'state': 'new',
            'ar_invoice_id': False,
            'original_ar_bill_id': False,
            'credit_note_ar_bill_id': False,
        })

        new_record = super(ARBill, self).copy(default)
        if not new_record:
            raise ValidationError("Failed to duplicate the record. Please check the configuration.")

        # Copy the bill lines
        for line in self.bill_line_ids:
            line_data = line.copy_data()[0]
            line_data.update({
                'ar_bill_id': new_record.id,
                'ar_invoice_line_id': False,  # Remove invoice line link
            })
            self.env['panexlogi.ar.bill.line'].create(line_data)

        # Copy the bill documents
        for doc in self.bill_doc_ids:
            doc_data = doc.copy_data()[0]
            doc_data['ar_bill_id'] = new_record.id
            self.env['panexlogi.ar.bill.doc'].create(doc_data)

        return new_record

    # compute receive amount from ar_invoice

    def _compute_receive_amount(self, compute=False):
        for record in self:
            record.receive_amount = 0.0
            record.invoice_amount = 0.0
            record.invoice_vat = 0.0
            record.invoice_amount_with_vat = 0.0
            if record.ar_invoice_id:
                if record.ar_invoice_id.state == 'confirm':
                    record.receive_amount = record.ar_invoice_id.receive_amount
                    record.invoice_amount = record.ar_invoice_id.invoice_amount
                    record.invoice_vat = record.ar_invoice_id.invoice_vat
                    record.invoice_amount_with_vat = record.ar_invoice_id.invoice_amount_with_vat

    # compute status from amount, invoice_amount, receive_amount
    def _compute_status(self):
        for record in self:
            if record.amount_with_vat > 0:  # POSITIVE
                if record.amount_with_vat - record.invoice_amount_with_vat > 0:
                    record.status = 'billed'
                elif record.amount_with_vat - record.invoice_amount_with_vat == 0:
                    if record.invoice_amount_with_vat - record.receive_amount > 0:
                        if record.receive_amount == 0:
                            record.status = 'invoiced'
                        else:
                            record.status = 'part received'
                    elif record.invoice_amount_with_vat - record.receive_amount == 0:
                        record.status = 'full received'
                    else:
                        record.status = 'other'
                else:
                    record.status = 'other'
            elif record.amount_with_vat < 0:  # NEGATIVE
                if record.amount_with_vat - record.invoice_amount_with_vat < 0:
                    if record.invoice_amount_with_vat - record.receive_amount > 0:
                        if record.receive_amount == 0:
                            record.status = 'invoiced'
                        else:
                            record.status = 'part received'
                    elif record.invoice_amount_with_vat - record.receive_amount == 0:
                        record.status = 'full received'
                    else:
                        record.status = 'other'
                else:
                    record.status = 'other'
            else:
                record.status = 'other'

    # dynamic domain for fiscal month
    @api.onchange('fiscal_year')
    def _onchange_fiscal_year(self):
        if self.fiscal_year:
            return {'domain': {'fiscal_month': [('year_id', '=', self.fiscal_year.id)]}}
        else:
            return {'domain': {'fiscal_month': []}}

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
        values['billno'] = self.env['ir.sequence'].next_by_code('seq.ar.bill', times)
        return super(ARBill, self).create(values)

    def action_confirm(self):
        for record in self:
            if record.state == 'new':
                # check is there is any line
                if not record.bill_line_ids:
                    raise UserError("Please add at least one line to the bill.")
                record.state = 'confirm'

                # Send Odoo message
                subject = 'A/R Bill Confirmed,please check it and create A/R Invoice'
                # Get base URL
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                # Construct URL to AR Bill
                ar_bill_id_url = "{}/web#id={}&model=panexlogi.ar.bill&view_type=form".format(
                    base_url,
                    record.id)
                # content
                content = f'''
                    <p>Hello,</p>
                    <p>An A/R Bill has been confirmed:</p>
                    <p><a href="{ar_bill_id_url}" style="color: #1A73E8; text-decoration: none; font-weight: bold;">View A/R Bill</a></p>
                    <p>Click the link above to access the details.</p>
                '''
                # Get users in the Finance group
                group = self.env['res.groups'].search([('name', '=', 'Finance')], limit=1)
                users = self.env['res.users'].search([('groups_id', '=', group.id)])
                # Get partner IDs from users
                partner_ids = users.mapped("partner_id").ids
                # Add Transport group users as followers
                record.message_subscribe(partner_ids=partner_ids)
                # Send message
                record.message_post(
                    body=content,
                    subject=subject,
                    message_type='notification',
                    subtype_xmlid="mail.mt_comment",  # Correct subtype for emails
                    body_is_html=True,  # Render HTML in email
                )
            else:
                raise UserError("Only new bills can be confirmed.")

    def action_cancel(self):
        for record in self:
            if record.state == 'new':
                if self.original_ar_bill_id:
                    # unlink the original bill
                    self.original_ar_bill_id.credit_note_ar_bill_id = False

                if self.credit_note_ar_bill_id:
                    raise UserError("This bill has a credit note, cannot be canceled.")

                record.state = 'cancel'
            else:
                raise UserError("Only new bills can be canceled.")

    def action_unconfirm(self):
        for record in self:
            if record.state == 'confirm':
                for line in self.bill_line_ids:
                    # check if the line is invoiced
                    if line.ar_invoice_line_id:
                        raise UserError("This bill has been invoiced, cannot be unconfirmed.")
                    # check if the line is invoiced
                    ar_invoice_line = self.env['panexlogi.ar.invoice.line'].search(
                        [('ar_bill_line_id', '=', line.id), ('ar_invoice_id.state', '!=', 'cancel')])
                    if ar_invoice_line:
                        raise UserError("This bill has been invoiced, cannot be unconfirmed.")
                # check if the bill is invoiced
                ar_invoice_line = self.env['panexlogi.ar.invoice.line'].search(
                    [('ab_bill_id', '=', self.id), ('ar_invoice_id.state', '!=', 'cancel')])
                if ar_invoice_line:
                    raise UserError("This bill has been invoiced, cannot be unconfirmed.")

                record.state = 'new'
            else:
                raise UserError("Only confirmed bills can be unconfirmed.")

    # sum lines amount,vat,amount_with_vat
    @api.depends('bill_line_ids.amount')
    def _compute_amount(self):
        for record in self:
            total_amount = 0.0
            for line in record.bill_line_ids:
                total_amount += line.amount
            record.amount = total_amount

    @api.depends('bill_line_ids.vat')
    def _compute_vat(self):
        for record in self:
            total_vat = 0.0
            for line in record.bill_line_ids:
                total_vat += line.vat
            record.vat = total_vat

    @api.depends('amount', 'vat')
    def _compute_amount_with_vat(self):
        for record in self:
            record.amount_with_vat = 0
            record.amount_with_vat = record.amount + record.vat

    # generate AR Invoice
    def generate_ar_invoice(self):
        self.ensure_one()
        # check if the bill is in confirm state
        if self.state != 'confirm':
            raise UserError("Only confirmed bills can generate AR Invoice.")
        # Check if the bill is already linked to an AR Invoice
        if self.ar_invoice_id:
            raise UserError("This bill already has an AR Invoice.")
        existing_invoice = self.env['panexlogi.ar.invoice'].search(
            [('ar_bill_id', '=', self.id), ('state', '!=', 'cancel')])
        if existing_invoice:
            raise UserError("This bill already has an AR Invoice.")
        for line in self.bill_line_ids:
            ar_invoice_line = self.env['panexlogi.ar.invoice.line'].search(
                [('ar_bill_line_id', '=', line.id), ('ar_invoice_id.state', '!=', 'cancel')])
            if ar_invoice_line:
                raise UserError("This bill already has an AR Invoice.")
        invoice_id = 0
        try:

            # Create AR Invoice from current bill
            invoice_vals = {
                'fiscal_year': self.fiscal_year.id,
                'fiscal_month': self.fiscal_month.id,
                'occurred_month': self.occurred_month,
                'project': self.project.id,
                'project_manager': self.project_manager.id,
                'customer': self.customer.id,
                'remark': self.remark,
                'ar_bill_id': self.id,
            }
            invoice = self.env['panexlogi.ar.invoice'].create(invoice_vals)
            invoice_id = invoice.id
            # Create invoice lines from bill lines
            for bill_line in self.bill_line_ids:
                invoice_line_vals = {
                    'ar_invoice_id': invoice.id,
                    'fitem': bill_line.fitem.id,
                    'invoice_amount': bill_line.amount,
                    'invoice_vat': bill_line.vat,
                    'invoice_amount_with_vat': bill_line.amount_with_vat,
                    'remark': bill_line.remark,
                    'ar_bill_line_id': bill_line.id,
                    'ab_bill_id': self.id,
                }
                invoice_line = self.env['panexlogi.ar.invoice.line'].create(invoice_line_vals)
                bill_line.ar_invoice_line_id = invoice_line.id

            # Update the ar_invoice_id
            self.ar_invoice_id = invoice.id  # Link bill to invoice
            self._compute_receive_amount()  # Recompute receive amount
            self._compute_status()  # Recompute status
        except Exception as e:
            # Rollback the created invoice if any error occurs
            invoice = self.env['panexlogi.ar.invoice'].browse(invoice_id)
            if invoice:
                invoice.unlink()
            _logger.error("Error creating AR Invoice: %s", e)
            raise UserError("Failed to create AR Invoice. Please check the logs for more details.")

        # Return action to view the created invoice
        return {
            'name': 'AR Invoice',
            'type': 'ir.actions.act_window',
            'res_model': 'panexlogi.ar.invoice',
            'view_mode': 'form',
            'res_id': invoice.id,
            'target': 'current',
        }

    # generate credit note
    def action_credit_note(self):
        self.ensure_one()
        new_bill = self.copy({
            'billno': self.env['ir.sequence'].next_by_code('seq.ar.bill'),
            'state': 'new',
            'ar_invoice_id': False,
            'original_ar_bill_id': False,
            'credit_note_ar_bill_id': False,
        })
        for line in new_bill.bill_line_ids:
            line.amount = -1 * line.amount
            line.vat = -1 * line.vat

        # Link the new credit note to the original bill
        self.credit_note_ar_bill_id = new_bill.id
        new_bill.original_ar_bill_id = self.id

        return {
            'name': 'Credit Note',
            'type': 'ir.actions.act_window',
            'res_model': 'panexlogi.ar.bill',
            'view_mode': 'form',
            'res_id': new_bill.id,
            'target': 'current',
        }


class ARBillLine(models.Model):
    _name = 'panexlogi.ar.bill.line'
    _description = 'panexlogi.ar.bill.line'

    fitem = fields.Many2one('panexlogi.fitems', string='Item(费用项目)', tracking=True)
    fitem_name = fields.Char(string='Item Name(费用项目名称)', related='fitem.name', readonly=True)
    amount = fields.Float(string="Amount")
    vat = fields.Float(string="VAT")
    amount_with_vat = fields.Float(string="Amount(with VAT)", compute="_compute_amount_with_vat", store=True)
    remark = fields.Text(string="Remark")
    ar_bill_id = fields.Many2one('panexlogi.ar.bill', string='AR Bill', ondelete='cascade')

    invoice_amount = fields.Float(string="Invoice Amount")
    invoice_vat = fields.Float(string="Invoice VAT")
    invoice_amount_with_vat = fields.Float(string="Invoice Amount(with VAT)")

    receive_amount = fields.Float(string="Receive Amount")
    receive_vat = fields.Float(string="Receive VAT")
    receive_amount_with_vat = fields.Float(string="Receive Amount(with VAT)")

    ar_invoice_line_id = fields.Many2one('panexlogi.ar.invoice.line', string='AR Invoice Line')

    @api.depends('amount', 'vat')
    def _compute_amount_with_vat(self):
        for record in self:
            record.amount_with_vat = 0
            record.amount_with_vat = record.amount + record.vat


class ARBillDoc(models.Model):
    _name = 'panexlogi.ar.bill.doc'
    _description = 'panexlogi.ar.bill.doc'

    remark = fields.Text(string="Remark")
    file = fields.Binary(string="File")
    file_name = fields.Char(string="File Name")
    ar_bill_id = fields.Many2one('panexlogi.ar.bill', string='AR Bill', ondelete='cascade')
