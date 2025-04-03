from odoo import _, models, fields, api, exceptions
from odoo.exceptions import UserError
import xlsxwriter
import base64
from io import BytesIO
from odoo.exceptions import ValidationError
import re


# settle shipping
class SettleShipping(models.Model):
    _name = 'panexlogi.settle.shipping'
    _description = 'panexlogi.settle.shipping'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = 'billno'

    billno = fields.Char(string='Bill No')
    # period = fields.Many2one('panexlogi.periods', string='Period', required=True)
    period = fields.Char(string='Period', required=True
                         ,
                         help='The period must be in the format YYYYMM and start with 20 (e.g., 202501, 202502, 202618).')
    start_date = fields.Date(string='Start Date', required=True)
    end_date = fields.Date(string='End Date', required=True)
    date_type = fields.Selection(selection=[('issue', 'Issue Date'), ('due', 'Due Date'), ('pay', 'Pay Date')],
                                 string='Date Type', default='issue')
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
    total_amount_usd = fields.Float(string='Total Amount USD', compute='get_total_amount', store=True)
    settle_shipping_detail_ids = fields.One2many('panexlogi.settle.shipping.detail', 'settle_shipping_id')
    settle_shipping_output_ids = fields.One2many('panexlogi.settle.shipping.output', 'settle_clearance_id')

    @api.model
    def create(self, values):
        """
        生成跟踪单号
        """
        times = fields.Date.today()
        values['billno'] = self.env['ir.sequence'].next_by_code('seq.settle.shipping', times)
        values['state'] = 'new'
        return super(SettleShipping, self).create(values)

    @api.model
    def write(self, values):
        res = super(SettleShipping, self).write(values)
        if 'start_date' in values or 'end_date' in values or 'project' in values:
            self.get_shipping_detail()
        return res

    @api.model
    def unlink(self):
        for rec in self:
            if rec.state != 'cancel':
                raise UserError(_("You only can delete Canceled Order"))
            else:
                rec.settle_shipping_detail_ids.unlink()

        return super(SettleShipping, self).unlink()

    def action_confirm_order(self):
        for rec in self:
            if rec.state != 'new':
                raise UserError(_("You only can confirm New Order"))
            else:
                rec.state = 'confirm'
                return True

    def action_cancel_order(self):
        for rec in self:
            if rec.state != 'new':
                raise UserError(_("You only can cancel New Order"))
            else:
                rec.state = 'cancel'
                return True

    def action_unconfirm_order(self):
        for rec in self:
            if rec.state != 'confirm':
                raise UserError(_("You only can unconfirm Confirmed Order"))
            else:
                rec.state = 'new'
                return True
    ""
    # check the combination of project,period is unique
    """
    @api.constrains('project', 'period')
    def _check_project_period(self):
        for rec in self:
            domain = [('project', '=', rec.project.id)
                , ('period', '=', rec.period.id)
                , ('state', '!=', 'cancel')
                , ('id', '!=', rec.id)]
            if self.env['panexlogi.settle.shipping'].search_count(domain) > 0:
                raise exceptions.ValidationError(_('The Project and Period must be unique!!'))
    """

    # 计算总金额
    @api.depends('settle_shipping_detail_ids.amount', 'settle_shipping_detail_ids.amount_usd')
    def get_total_amount(self):
        for rec in self:
            total_amount = 0
            total_amount_usd = 0
            for detail in rec.settle_shipping_detail_ids:
                total_amount += detail.amount
                total_amount_usd += detail.amount_usd
            rec.total_amount = total_amount
            rec.total_amount_usd = total_amount_usd

    # user choose different date type to get shipping invoice detail
    def get_shipping_detail(self):
        for rec in self:
            # 条件: project=project, state in confirm,apply,paid, date>=start_date, date<=end_date
            domain = [('waybill_billno.project', '=', rec.project.id),
                      ('state', 'in', ['confirm', 'apply', 'paid']), ]
            # '&',
            # ('date', '>=', rec.start_date),  # ShipInvoice's date
            # ('date', '<=', rec.end_date)]
            shipping_invoices = self.env['panexlogi.waybill.shipinvoice'].search(domain)
            if shipping_invoices:
                # user confirm to unlink all the details
                rec.settle_shipping_detail_ids.unlink()
                settle_shipping_detail = []
                rec.settle_shipping_detail_ids = False
                for invoice in shipping_invoices:
                    cntrnos = ','.join([str(x) for x in invoice.waybill_billno.details_ids.mapped('cntrno')])
                    cntrqty = len(invoice.waybill_billno.details_ids.mapped('cntrno'))
                    # get paymentapplication
                    paymentapplication = self.env['panexlogi.finance.paymentapplication'].search([
                        ('source', '=', 'Shipping Invoice')
                        , ('state', 'in', ['confirm', 'apply', 'paid'])
                        , '|', ('invoiceno', '=', invoice.invno), ('shipinvoice_id', '=', invoice.id)]
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
                        for line_detail in invoice.waybillshipinvoicedetail_ids:
                            settle_shipping_detail.append((0, 0, {
                                'jobno': invoice.waybill_billno.docno,
                                'invoice_id': invoice.id,
                                # 'invoiceno': invoice.invno,
                                'payment_id': payment_id,
                                'waybill_id': invoice.waybill_billno.id,
                                'waybillno': invoice.waybill_billno.waybillno,
                                'Container': cntrnos,
                                'shipping': invoice.waybill_billno.shipping.id,
                                'container_qty': cntrqty,
                                'fitem': line_detail.fitem.id,
                                'amount': line_detail.amount,
                                'amount_usd': line_detail.amount_usd,
                                'remark': line_detail.remark,
                            }))
                rec.settle_shipping_detail_ids = settle_shipping_detail

    # print to excel

    def print_detail_to_excel(self):
        for rec in self:

            if not rec.settle_shipping_detail_ids:
                raise exceptions.ValidationError(_('No data to print!!'))

            output = BytesIO()
            workbook = xlsxwriter.Workbook(output, {'in_memory': True})
            worksheet = workbook.add_worksheet('Settle Clearance Details')

            # Define the headers
            headers = ['Invoice ID', 'Invoice No', 'Waybill ID', 'Job No', 'Waybill No', 'Container',
                       'Container Quantity', 'Item', 'Item_name', 'Amount_EUR', 'Amount_USD', 'Remark']

            # Define a format with border
            border_format = workbook.add_format({'border': 1})

            for col_num, header in enumerate(headers):
                worksheet.write(0, col_num, header, border_format)

            # Write the data
            row = 1
            for detail in rec.settle_shipping_detail_ids:
                worksheet.write(row, 0, detail.invoice_id.billno, border_format)
                worksheet.write(row, 1, detail.invoiceno, border_format)
                worksheet.write(row, 2, detail.waybill_id.billno, border_format)
                worksheet.write(row, 3, detail.jobno if detail.jobno else '', border_format)
                worksheet.write(row, 4, detail.waybillno, border_format)
                worksheet.write(row, 5, detail.Container, border_format)
                worksheet.write(row, 6, detail.container_qty, border_format)
                worksheet.write(row, 7, detail.fitem.code, border_format)
                worksheet.write(row, 8, detail.fitem.name, border_format)
                worksheet.write(row, 9, detail.amount, border_format)
                worksheet.write(row, 10, detail.amount_usd, border_format)
                worksheet.write(row, 11, detail.remark if detail.remark else '', border_format)
                row += 1

            workbook.close()
            output.seek(0)
            # rec.pdffile = base64.b64encode(output.read())
            # rec.pdffilename = 'Settle_Clearance_Details.xlsx'

            # To send the generated Excel file as an attachment in a message
            file_data = output.read()
            rec.settle_shipping_output_ids.create({
                'settle_clearance_id': rec.id,
                'description': 'Settle Shipping Details(%s)' % fields.Datetime.now(),
                'excel_file': base64.b64encode(file_data),
                'excel_filename': 'Settle_Shipping_Details.xlsx'
            })
            output.close()

            """
            attachment = ('Settle_Shipping_Details.xlsx', file_data)
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
                raise ValidationError(_("The period must be in the format YYYYMM (e.g., 202501, 202502, 202618)."))

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


class SettleShippingDetail(models.Model):
    _name = 'panexlogi.settle.shipping.detail'
    _description = 'panexlogi.settle.shipping.detail'

    # Add related project field
    project_id = fields.Many2one(
        'panexlogi.project',
        string='Project',
        related='settle_shipping_id.project',
        store=True
    )
    jobno = fields.Char(string='Job No')
    invoice_id = fields.Many2one('panexlogi.waybill.shipinvoice', string='Invoice ID'
                                 , help='Link to Shipping Invoice.')
    # ,domain=[('state', 'in', ['confirm', 'apply', 'paid']),('waybill_billno.project', '=', project_id.id)])
    invoiceno = fields.Char(string='Invoice No', related='invoice_id.invno', readonly=True)
    invoice_date = fields.Date(string='Issue Date', related='invoice_id.date', readonly=True)
    due_date = fields.Date(string='Due Date', related='invoice_id.due_date', readonly=True)
    payment_id = fields.Many2one('panexlogi.finance.payment', string='Payment ID', readonly=True
                                 , help='Link to Payment.')
    pay_date = fields.Date(string='Pay Date', related='payment_id.pay_date', readonly=True)
    waybill_id = fields.Many2one('panexlogi.waybill', string='Waybill ID', readonly=True
                                 , help='Link to Waybill.')
    waybillno = fields.Char(string='BL No', related='waybill_id.waybillno', readonly=True)
    Container = fields.Char(string='Container'
                            , help='All of containers.', readonly=True)
    shipping = fields.Many2one('res.partner', string='Shipping Line', readonly=True)
    container_qty = fields.Char(string='Container Quantity', readonly=True)
    fitem = fields.Many2one('panexlogi.fitems', string='Item(费用项目)', readonly=True)
    fitem_name = fields.Char(string='Item Name(费用项目名称)', related='fitem.name', readonly=True)
    amount = fields.Float(string='Amount（欧元金额）', tracking=True)
    amount_usd = fields.Float(string='Amount（美元金额）', tracking=True)
    remark = fields.Text(string='Remark', tracking=True)

    settle_shipping_id = fields.Many2one('panexlogi.settle.shipping', string='Settle Shipping')

    """
    @api.onchange('invoice_id')
    def _compute_waybill(self):
        for rec in self:
            rec.invoice_id = rec.invoice_id.invno
            rec.waybill_id = rec.invoice_id.waybill_billno.id
            rec.jobno = rec.invoice_id.waybill_billno.docno
            rec.Container = ','.join([str(x) for x in rec.invoice_id.waybill_billno.details_ids.mapped('cntrno')])
            rec.container_qty = len(rec.invoice_id.waybill_billno.details_ids.mapped('cntrno'))
    
    # check invoice_id unique
    @api.constrains('invoice_id')
    def _check_invoice_id(self):
        for rec in self:
            if rec.invoice_id:
                domain = [('invoice_id', '=', rec.invoice_id.id)
                    , ('id', '!=', rec.id)
                    , ('settle_shipping_id.state', '!=', 'cancel')]
                if self.search_count(domain) > 0:
                    raise exceptions.ValidationError(_('The Invoice ID must be unique!!'))
    """


class SettleShippingOutput(models.Model):
    _name = 'panexlogi.settle.shipping.output'
    _description = 'panexlogi.settle.shipping.output'

    settle_clearance_id = fields.Many2one('panexlogi.settle.shipping', string='Settle Shipping')
    description = fields.Char(string='Description')
    excel_file = fields.Binary(string='File')
    excel_filename = fields.Char(string='File name')
