from odoo import _, models, fields, api, exceptions
from odoo.exceptions import UserError
import xlsxwriter
import base64
from io import BytesIO
from odoo.exceptions import ValidationError
import re


# settle shipping
class SettleClearance(models.Model):
    _name = 'panexlogi.settle.clearance'
    _description = 'panexlogi.settle.clearance'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = 'billno'

    billno = fields.Char(string='Bill No')
    # period = fields.Many2one('panexlogi.periods', string='Period', required=True)
    period = fields.Char(string='Period', required=True
                         ,
                         help='The period must be in the format YYYYMM and start with 20 (e.g., 202501, 202502, 202618).')
    start_date = fields.Date(string='Start Date', required=True)
    date_type = fields.Selection(selection=[('issue', 'Issue Date'), ('due', 'Due Date'), ('pay', 'Pay Date')],
                                 string='Date Type', default='issue')
    end_date = fields.Date(string='End Date', required=True)
    project = fields.Many2one('panexlogi.project', string='Project', required=True)
    remark = fields.Text(string='Remark')
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
    pdffile = fields.Binary(string='File')
    pdffilename = fields.Char(string='File name')
    total_amount = fields.Float(string='Total Amount', compute='get_total_amount', store=True)
    total_amount_invoice = fields.Float(string='Total Amount of Invoice', compute='get_total_amount', store=True)
    settle_clearance_detail_ids = fields.One2many('panexlogi.settle.clearance.detail', 'settle_clearance_id')
    settle_clearance_output_ids = fields.One2many('panexlogi.settle.clearance.output', 'settle_clearance_id')

    @api.model
    def create(self, values):
        """
        生成跟踪单号
        """
        times = fields.Date.today()
        values['billno'] = self.env['ir.sequence'].next_by_code('seq.settle.clearance', times)
        return super(SettleClearance, self).create(values)

    @api.model
    def write(self, values):
        res = super(SettleClearance, self).write(values)
        if 'start_date' in values or 'end_date' in values or 'project' in values:
            self.get_clearance_detail()
        return res

    @api.model
    def unlink(self):
        for rec in self:
            if rec.state != 'cancel':
                raise UserError(_("You only can delete Canceled Order"))
            else:
                rec.settle_shipping_detail_ids.unlink()

        return super(SettleClearance, self).unlink()

    def action_confirm_order(self):
        for rec in self:
            if rec.state != 'new':
                raise UserError(_("You only can confirm New Order"))
            else:
                return {
                    'type': 'ir.actions.act_window',
                    'name': 'Update Clearance',
                    'res_model': 'panexlogi.settle.clearance.update.wizard',
                    'view_mode': 'form',
                    'target': 'new',
                    'context': {'default_settle_clearance_id': rec.id},
                }

    # Existing fields and methods...
    # Update Waybill POA fields
    def _update_poa_fields(self):
        for rec in self:
            rec.state = 'confirm'
            for detail in rec.settle_clearance_detail_ids:
                if detail.clearinvoice_detail_id:
                    detail.clearinvoice_detail_id.poa = detail.poa
                    detail.clearinvoice_detail_id.t1 = detail.t1
                    detail.clearinvoice_detail_id.vdn = detail.vdn
                    detail.clearinvoice_detail_id.imd = detail.imd
                    detail.clearinvoice_detail_id.exa = detail.exa
                    detail.clearinvoice_detail_id.lfr = detail.lfr
                    detail.clearinvoice_detail_id.expa = detail.expa

    def _not_update_poa_fields(self):
        for rec in self:
            rec.state = 'confirm'

    def action_cancel_order(self):
        for rec in self:
            if rec.state != 'new':
                raise UserError(_("You only can cancel New Order"))
            else:
                # rec.state = 'cancel'
                # return True
                return {
                    'type': 'ir.actions.act_window',
                    'name': 'Reset Clearance',
                    'res_model': 'panexlogi.settle.clearance.reset.wizard',
                    'view_mode': 'form',
                    'target': 'new',
                    'context': {'default_settle_clearance_id': rec.id},
                }

    def action_unconfirm_order(self):
        for rec in self:
            if rec.state != 'confirm':
                raise UserError(_("You only can unconfirm Confirmed Order"))
            else:
                # rec.state = 'new'
                # return True
                return {
                    'type': 'ir.actions.act_window',
                    'name': 'Reset Clearance',
                    'res_model': 'panexlogi.settle.clearance.reset.wizard',
                    'view_mode': 'form',
                    'target': 'new',
                    'context': {'default_settle_clearance_id': rec.id},
                }

    # reset the poa field in the related WaybillClearInvoice
    def _reset_poa(self, state):
        for rec in self:
            rec.state = state
            for detail in rec.settle_clearance_detail_ids:
                if detail.clearinvoice_detail_id:
                    detail.clearinvoice_detail_id.poa = 0
                    detail.clearinvoice_detail_id.t1 = 0
                    detail.clearinvoice_detail_id.vdn = 0
                    detail.clearinvoice_detail_id.imd = 0
                    detail.clearinvoice_detail_id.exa = 0
                    detail.clearinvoice_detail_id.lfr = 0
                    detail.clearinvoice_detail_id.expa = 0

    def _dont_reset_poa(self, state):
        for rec in self:
            rec.state = state

    # 计算总金额
    @api.depends('settle_clearance_detail_ids.amount', 'settle_clearance_detail_ids.invoice_amount')
    def get_total_amount(self):
        for rec in self:
            total_amount = 0
            total_amount_invoice = 0
            for detail in rec.settle_clearance_detail_ids:
                total_amount += detail.amount
                total_amount_invoice += detail.invoice_amount
            rec.total_amount = total_amount
            rec.total_amount_invoice = total_amount_invoice

    # get clearance detail
    def get_clearance_detail(self):
        for rec in self:
            try:
                # 条件: project=project, state in confirm,apply,paid, date>=start_date, date<=end_date
                domain = [('waybill_billno.project', '=', rec.project.id),
                          ('state', 'in', ['confirm', 'apply', 'paid']), ]
                # '&',
                # ('date', '>=', rec.start_date),  # ShipInvoice's date
                # ('date', '<=', rec.end_date)]
                clearance_invoices = self.env['panexlogi.waybill.clearinvoice'].search(domain)
                if clearance_invoices:
                    # user confirm to unlink all the details
                    rec.settle_clearance_detail_ids.unlink()
                    settle_clearance_detail = []
                    # rec.settle_clearance_detail_ids = False
                    for invoice in clearance_invoices:
                        cntrnos = ','.join([str(x) for x in invoice.waybill_billno.details_ids.mapped('cntrno')])
                        cntrqty = len(invoice.waybill_billno.details_ids.mapped('cntrno'))
                        # get paymentapplication
                        paymentapplication = self.env['panexlogi.finance.paymentapplication'].search([
                            ('source', '=', 'Clearance Invoice')
                            , ('state', 'in', ['confirm', 'apply', 'paid'])
                            , '|', ('invoiceno', '=', invoice.invno), ('clearinvoice_id', '=', invoice.id)]
                            , limit=1)
                        payment_id = 0
                        pay_date = False
                        if paymentapplication:
                            if paymentapplication.payment_id:
                                payment = self.env['panexlogi.finance.payment'].search(
                                    [('id', '=', paymentapplication.payment_id.id), ('state', '=', 'paid')], limit=1)
                                if payment:
                                    payment_id = payment.id
                                    pay_date = payment.pay_date
                        # check date return bcheck
                        bcheck = False
                        if rec.date_type == 'issue':
                            if invoice.date >= rec.start_date and invoice.date <= rec.end_date:
                                bcheck = True
                        elif rec.date_type == 'due':
                            if invoice.due_date >= rec.start_date and invoice.due_date <= rec.end_date:
                                bcheck = True
                        elif rec.date_type == 'pay':
                            if pay_date:
                                if (pay_date >= rec.start_date and pay_date <= rec.end_date):
                                    bcheck = True

                        if bcheck:
                            for detail in invoice.waybillclearinvoicedetail_ids:
                                if detail:
                                    clearance_type = detail.clearance_type.id if detail.clearance_type else False

                                    settle_clearance_detail.append((0, 0, {
                                        'jobno': invoice.waybill_billno.docno,
                                        'invoice_id': invoice.id,
                                        # 'invoiceno': invoice.invno,
                                        'payment_id': payment_id,
                                        'waybill_id': invoice.waybill_billno.id,
                                        'waybillno': invoice.waybill_billno.waybillno,
                                        'Container': cntrnos,
                                        'container_qty': cntrqty,
                                        'clearinvoice_detail_id': detail.id,
                                        'clearance_type': clearance_type,
                                        'poa': detail.poa,
                                        't1': detail.t1,
                                        'vdn': detail.vdn,
                                        'imd': detail.imd,
                                        'exa': detail.exa,
                                        'lfr': detail.lfr,
                                        'expa': detail.expa,
                                        'invoice_amount': invoice.eurtotal,
                                        'remark': invoice.desc,
                                    }))
                    rec.settle_clearance_detail_ids = settle_clearance_detail
            except Exception as e:
                raise UserError(_('An error occurred while getting clearance details: %s') % str(e))

    # print to excel

    def print_detail_to_excel(self):
        for rec in self:

            if not rec.settle_clearance_detail_ids:
                raise exceptions.ValidationError(_('No data to print!!'))

            output = BytesIO()
            workbook = xlsxwriter.Workbook(output, {'in_memory': True})
            worksheet = workbook.add_worksheet('Settle Clearance Details')

            # Define the headers
            headers = ['Invoice ID', 'Invoice No', 'Waybill ID', 'Job No', 'Waybill No', 'Container',
                       'Container Quantity', 'POA', 'T1', 'VAT defer notification', 'Import declaration',
                       'Extra article', 'LFR', 'Amount',
                       'Invoice Amount', 'Remark', 'Export']

            # Define a format with border
            border_format = workbook.add_format({'border': 1})

            for col_num, header in enumerate(headers):
                worksheet.write(0, col_num, header, border_format)

            # Write the data
            row = 1
            for detail in rec.settle_clearance_detail_ids:
                worksheet.write(row, 0, detail.invoice_id.billno, border_format)
                worksheet.write(row, 1, detail.invoiceno, border_format)
                worksheet.write(row, 2, detail.waybill_id.billno, border_format)
                worksheet.write(row, 3, detail.jobno if detail.jobno else '', border_format)
                worksheet.write(row, 4, detail.waybillno, border_format)
                worksheet.write(row, 5, detail.Container if detail.Container else '', border_format)
                worksheet.write(row, 6, detail.container_qty, border_format)
                # worksheet.write(row, 7, detail.fitem.name, border_format)
                worksheet.write(row, 7, detail.poa, border_format)
                worksheet.write(row, 8, detail.t1, border_format)
                worksheet.write(row, 9, detail.vdn, border_format)
                worksheet.write(row, 10, detail.imd, border_format)
                worksheet.write(row, 11, detail.exa, border_format)
                worksheet.write(row, 12, detail.lfr, border_format)
                worksheet.write(row, 13, detail.amount, border_format)
                worksheet.write(row, 14, detail.invoice_amount, border_format)
                worksheet.write(row, 15, detail.remark if detail.remark else '', border_format)
                worksheet.write(row, 16, detail.expa, border_format)
                row += 1

            workbook.close()
            output.seek(0)
            # rec.pdffile = base64.b64encode(output.read())
            # rec.pdffilename = 'Settle_Clearance_Details.xlsx'

            # To send the generated Excel file as an attachment in a message
            file_data = output.read()
            rec.settle_clearance_output_ids.create({
                'settle_clearance_id': rec.id,
                'description': 'Settle Clearance Details(%s)' % fields.Datetime.now(),
                'excel_file': base64.b64encode(file_data),
                'excel_filename': 'Settle_Clearance_Details.xlsx'
            })
            output.close()

            """
            attachment = ('Settle_Clearance_Details.xlsx', file_data)
            rec.message_post(
                body='Please find the attached Settle Clearance Details.',
                subject='Settle Clearance Details',
                message_type='notification',
                subtype_xmlid="mail.mt_comment",  # Correct subtype for emails
                attachments=[attachment]
            )
            """
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': 'Output details successfully!',
                'type': 'success',
                'sticky': False,
                'next': {
                    'type': 'ir.actions.client',
                    'tag': 'reload',
                }
            }
        }

    @api.constrains('period')
    def _check_period_format(self):
        pattern = re.compile(r'^20\d{4}$')
        for rec in self:
            if not pattern.match(rec.period):
                raise ValidationError(
                    _("The period must be in the format YYYYMM and start with '20' (e.g., 202501, 202502, 202618)."))

    # check the combination of project,period is unique
    """
    @api.constrains('project', 'period')
    def _check_project_period(self):
        for rec in self:
            domain = [('project', '=', rec.project.id)
                , ('period', '=', rec.period)
                , ('state', '!=', 'cancel')
                , ('id', '!=', rec.id)]
            if self.search_count(domain) > 0:
                raise exceptions.ValidationError(_('The Project and Period must be unique!!'))
    """


class SettleClearanceDetail(models.Model):
    _name = 'panexlogi.settle.clearance.detail'
    _description = 'panexlogi.settle.clearance.detail'

    settle_clearance_id = fields.Many2one('panexlogi.settle.clearance', string='Settle Clearance')
    jobno = fields.Char(string='Job No')
    invoice_id = fields.Many2one('panexlogi.waybill.clearinvoice', string='Invoice ID')
    invoiceno = fields.Char(string='Invoice No', related='invoice_id.invno', readonly=True)
    invoice_date = fields.Date(string='Issue Date', related='invoice_id.date', readonly=True)
    due_date = fields.Date(string='Due Date', related='invoice_id.due_date', readonly=True)
    payment_id = fields.Many2one('panexlogi.finance.payment', string='Payment ID', readonly=True
                                 , help='Link to Payment.')
    pay_date = fields.Date(string='Pay Date', related='payment_id.pay_date', readonly=True)
    waybill_id = fields.Many2one('panexlogi.waybill', string='Waybill ID', readonly=True)
    waybillno = fields.Char(string='BL No', readonly=True)
    Container = fields.Char(string='Container', readonly=True)
    container_qty = fields.Char(string='Container Quantity', readonly=True)
    clearinvoice_detail_id = fields.Many2one('panexlogi.waybill.clearinvoice.detail', )
    clearance_type = fields.Many2one('panexlogi.clearance.type', string='Clearance Type', tracking=True)
    fitem = fields.Many2one('panexlogi.fitems', string='Item(费用项目)', tracking=True)
    fitem_name = fields.Char(string='Item Name(费用项目名称)', related='fitem.name', readonly=True)
    poa = fields.Float(string='POA', tracking=True, default=0)
    t1 = fields.Float(string='T1', tracking=True, default=0)
    vdn = fields.Float(string='VAT defer notification', tracking=True, default=0)
    imd = fields.Float(string='Import declaration', tracking=True, default=0)
    exa = fields.Float(string='Extra article', tracking=True, default=0)
    lfr = fields.Float(string='LFR', tracking=True, default=0)
    expa = fields.Float(string='Export', tracking=True, default=0)
    amount = fields.Float(string='Amount（欧元金额）', compute='get_total_amount', store=True)
    invoice_amount = fields.Float(string='Invoice Amount(发票金额)', readonly=True)
    remark = fields.Text(string='Remark', tracking=True)

    @api.depends('poa', 't1', 'vdn', 'imd', 'exa', 'lfr', 'expa')
    def get_total_amount(self):
        for rec in self:
            amount = 0
            amount += rec.poa + rec.t1 + rec.vdn + rec.imd + rec.exa + rec.lfr + rec.expa
            rec.amount = amount

    """
    @api.constrains('invoice_id')
    def _check_invoice_id(self):
        for rec in self:
            if rec.invoice_id:
                domain = [('invoice_id', '=', rec.invoice_id.id)
                    , ('id', '!=', rec.id)
                    , ('settle_clearance_id.state', '!=', 'cancel')]
                if self.search_count(domain) > 0:
                    raise exceptions.ValidationError(_('The Invoice ID must be unique!!'))
    """


class SettleClearanceOutput(models.Model):
    _name = 'panexlogi.settle.clearance.output'
    _description = 'panexlogi.settle.clearance.output'

    settle_clearance_id = fields.Many2one('panexlogi.settle.clearance', string='Settle Clearance')
    description = fields.Char(string='Description')
    excel_file = fields.Binary(string='File')
    excel_filename = fields.Char(string='File name')


# Reset Clearance Wizard
class ResetWaybillClearanceWizard(models.TransientModel):
    _name = 'panexlogi.settle.clearance.reset.wizard'
    _description = 'panexlogi.settle.clearance.reset.wizard'

    settle_clearance_id = fields.Many2one('panexlogi.settle.clearance', string='Settle Clearance')
    state = fields.Char(string='State', compute='_get_sate', store=True)

    @api.depends('settle_clearance_id')
    def _get_sate(self):
        for rec in self:
            settle_clearance_id = rec.settle_clearance_id
            state = settle_clearance_id.state
            if state == 'confirm':
                rec.state = 'new'
            elif state == 'new':
                rec.state = 'cancel'

    def action_reset_poa(self):
        self.settle_clearance_id._reset_poa(self.state)
        return {'type': 'ir.actions.act_window_close'}

    def action_dont_reset_poa(self):
        self.settle_clearance_id._dont_reset_poa(self.state)
        return {'type': 'ir.actions.act_window_close'}

    def action_cancel(self):
        return {'type': 'ir.actions.act_window_close'}


# Confirm Update POA Wizard
class ConfirmUpdateWaybillClearanceWizard(models.TransientModel):
    _name = 'panexlogi.settle.clearance.update.wizard'
    _description = 'panexlogi.settle.clearance.update.wizard'

    settle_clearance_id = fields.Many2one('panexlogi.settle.clearance', string='Settle Clearance')

    def action_confirm(self):
        self.settle_clearance_id._update_poa_fields()
        return {'type': 'ir.actions.act_window_close'}

    def action_not_confirm(self):
        self.settle_clearance_id._not_update_poa_fields()
        return {'type': 'ir.actions.act_window_close'}

    def action_cancel(self):
        return {'type': 'ir.actions.act_window_close'}
