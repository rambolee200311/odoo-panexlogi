from odoo import _, models, fields, api
from datetime import timedelta

from odoo.exceptions import UserError


# 清关费用发票

class WaybillClearInvoice(models.Model):
    _name = 'panexlogi.waybill.clearinvoice'
    _description = 'panexlogi.waybill.clearinvoice'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = 'billno'

    payee = fields.Many2one('res.partner', string='Payee（收款人）', required=True)
    billno = fields.Char(string='Commer Invoice No', readonly=True, tracking=True)
    invno = fields.Char(string='Invoice No（发票号）', required=True, tracking=True)
    date = fields.Date(string='Issue Date（发票日期）', required=True, tracking=True)
    due_date = fields.Date(string='Due Date（到期日）', required=True,
                           tracking=True)
    desc = fields.Char(string='Description(费用名称)', tracking=True)
    usdtotal = fields.Float(string='Total_of_USD', store=True,
                            tracking=True, compute='_compute_total')
    eurtotal = fields.Float(string='Total_of_EUR', store=True,
                            tracking=True, compute='_compute_total')
    pdffile = fields.Binary(string='File（原件）')
    pdffilename = fields.Char(string='File name')
    waybill_billno = fields.Many2one('panexlogi.waybill')

    project = fields.Many2one('panexlogi.project', string='Project（项目）', compute='_get_waybill')
    color = fields.Integer()
    state = fields.Selection(
        selection=[
            ('new', 'New'),
            ('confirm', 'Confirm'),
            ('cancel', 'Cancel'),
            ('apply', 'Apply Pay'),
            ('paid', 'Paid'),
        ],
        default='new',
        string="State",
        tracking=True
    )
    waybill_application = fields.Many2one('panexlogi.finance.paymentapplication', 'Waybill Application')
    waybillclearinvoicedetail_ids = fields.One2many('panexlogi.waybill.clearinvoice.detail', 'clearinvoiceinvoiceid')

    poa = fields.Float(string='POA', readonly=True, tracking=True, compute='_compute_total')
    t1 = fields.Float(string='T1', readonly=True, tracking=True, compute='_compute_total')
    vdn = fields.Float(string='VAT defer notification', readonly=True, tracking=True, compute='_compute_total')
    imd = fields.Float(string='Import declaration', readonly=True, tracking=True, compute='_compute_total')
    exa = fields.Float(string='Extra article', readonly=True, tracking=True, compute='_compute_total')
    lfr = fields.Float(string='LFR', readonly=True, tracking=True, compute='_compute_total')
    expa = fields.Float(string='Export', readonly=True, tracking=True, compute='_compute_total')
    cntrnos = fields.Char(string='Container No(集装箱号)', compute='_get_cntrno_refno')
    refnos = fields.Char(string='Reference No(参考号)', compute='_get_cntrno_refno')

    @api.model
    def create(self, values):
        """
        生成跟踪单号
        """
        times = fields.Date.today()
        values['billno'] = self.env['ir.sequence'].next_by_code('seq.waybill.clearinvoice', times)
        return super(WaybillClearInvoice, self).create(values)

    @api.onchange('waybill_billno')
    def _get_waybill(self):
        for r in self:
            self.project = self.waybill_billno.project

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

    @api.depends('waybillclearinvoicedetail_ids')
    def _compute_total(self):
        for rec in self:
            rec.eurtotal = 0
            rec.usdtotal = 0
            rec.poa = 0
            rec.t1 = 0
            rec.vdn = 0
            rec.imd = 0
            rec.exa = 0
            rec.lfr = 0
            rec.expa = 0
            if rec.waybillclearinvoicedetail_ids:
                rec.eurtotal = sum(rec.waybillclearinvoicedetail_ids.mapped('amount'))
                rec.usdtotal = sum(rec.waybillclearinvoicedetail_ids.mapped('amount_usd'))
                rec.poa = sum(rec.waybillclearinvoicedetail_ids.mapped('poa'))
                rec.t1 = sum(rec.waybillclearinvoicedetail_ids.mapped('t1'))
                rec.vdn = sum(rec.waybillclearinvoicedetail_ids.mapped('vdn'))
                rec.imd = sum(rec.waybillclearinvoicedetail_ids.mapped('imd'))
                rec.exa = sum(rec.waybillclearinvoicedetail_ids.mapped('exa'))
                rec.lfr = sum(rec.waybillclearinvoicedetail_ids.mapped('lfr'))
                rec.expa = sum(rec.waybillclearinvoicedetail_ids.mapped('expa'))

    # Create PaymentApplication
    def create_payment_application(self):
        # Create PaymentApplication
        for record in self:
            # check if state is confirm
            if record.state != 'confirm':
                raise UserError(_("You can only create Payment Application for a confirmed Clearance Invoice"))
            # Check if PaymentApplication already exists
            direction = record.waybill_billno.direction
            domain1 = [
                ('source', '=', 'Clearance Invoice')
                , ('source_Code', '=', record.billno)
                , ('state', '!=', 'cancel')
                , ('type', '=', direction)
            ]
            existing_records = self.env['panexlogi.finance.paymentapplication'].search(domain1)
            if existing_records:
                existing_billnos = ", ".join(existing_records.mapped('billno'))
                raise UserError(_
                                ("Payment Application [%(billno)s] already exists for this Clearance Invoice '%(suorce)s'") %
                                {
                                    'billno': existing_billnos, 'suorce': record.billno
                                })
            # check if invoiceno is duplicate
            domain2 = [
                ('source', '=', 'Clearance Invoice')
                , ('waybill_billno', '=', record.waybill_billno.id)
                , ('invoiceno', '=', record.invno)
                , ('state', '!=', 'cancel')
                , ('type', '=', direction)]
            existing_records = self.env['panexlogi.finance.paymentapplication'].search(domain2)
            if existing_records:
                existing_billnos = ", ".join(existing_records.mapped('billno'))
                raise UserError(_(
                    "Invoice No '%(invno)s' is already used in Payment Application(s) [%(billnos)s] for Waybill '%(waybill)s'."
                ) % {
                                    'invno': record.invno,
                                    'billnos': existing_billnos,
                                    'waybill': record.waybill_billno.waybillno
                                })
            # check if payee is selected
            if not record.payee.id:
                raise UserError(_("Please select a Payee"))
            # Create PaymentApplication
            payment_application = self.env['panexlogi.finance.paymentapplication'].create({
                'date': fields.Date.today(),
                'type': direction,
                'source': 'Clearance Invoice',
                'payee': record.payee.id,
                'source_Code': record.billno,
                'pdffile': record.pdffile,
                'pdffilename': record.pdffilename,
                'invoiceno': record.invno,
                'invoice_date': record.date,
                'due_date': record.due_date,
                'waybill_billno': record.waybill_billno.id,
                'clearinvoice_id': record.id
            })
            for records in record.waybillclearinvoicedetail_ids:
                # Create PaymentApplicationLine
                if records.amount != 0 or records.amount_usd != 0:
                    self.env['panexlogi.finance.paymentapplicationline'].create({
                        'fitem': records.fitem.id,
                        'payapp_billno': payment_application.id,
                        'amount': records.amount,
                        'amount_usd': records.amount_usd,
                        'remark': records.remark,
                        'project': record.project.id,
                    })
            record.state = 'apply'
            record.waybill_application = payment_application.id
            # Send Odoo message
            subject = 'Payment Application Created'
            # Get base URL
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            # Construct URL to transport order
            transport_order_url = "{}/web#id={}&model=panexlogi.finance.paymentapplication&view_type=form".format(
                base_url,
                payment_application.id)
            # content = 'Transport order: <a href="{}">{}</a> created successfully!'.format(transport_order_url,
            #                                                                              payment_application.billno)
            # HTML content with button styling
            content = f'''
                        <p>Hello,</p>
                        <p>A new Payment application has been created:</p>                                
                        <p>Click the button above to access the details.</p>
                        '''
            # Get users in the Finance group
            group = self.env['res.groups'].search([('name', '=', 'Finance')], limit=1)
            users = self.env['res.users'].search([('groups_id', '=', group.id)])
            # Get partner IDs from users
            partner_ids = users.mapped("partner_id").ids
            # Add Transport group users as followers
            payment_application.message_subscribe(partner_ids=partner_ids)
            # Send message
            payment_application.message_post(
                body=content,
                subject=subject,
                message_type='notification',
                subtype_xmlid="mail.mt_comment",  # Correct subtype for emails
                body_is_html=True,  # Render HTML in email
            )
            # force_send=True,
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': 'Import Payment Application create successfully!',
                'type': 'success',
                'sticky': False,
            }
        }

    # unlink method
    def unlink(self):
        for record in self:
            domain = [
                ('source', '=', 'Clearance Invoice'),
                ('source_Code', '=', record.billno),
                ('state', '!=', 'cancel'),
                ('type', '=', 'import')
            ]
            existing_records = self.env['panexlogi.finance.paymentapplication'].search(domain)
            if existing_records:
                raise UserError(_('You cannot delete a Clearance Invoice that has a Payment Application.'))
        return super(WaybillClearInvoice, self).unlink()

    # check invno unique in each waybill
    @api.constrains('invno', 'waybill_billno')
    def _check_invno(self):
        for r in self:
            # when not unique, raise error
            domain = [('invno', '=', r.invno)
                , ('id', '!=', r.id)
                , ('waybill_billno', '=', r.waybill_billno.id)
                , ('state', '!=', 'cancel')]
            if self.search_count(domain) > 0:
                raise UserError(_(
                    "Invoice No '%(invno)s' must be unique within Waybill '%(waybill)s'."
                ) % {
                                    'invno': r.invno,
                                    'waybill': r.waybill_billno.waybillno
                                })

    @api.depends('waybillclearinvoicedetail_ids.cntrno', 'waybillclearinvoicedetail_ids.refno')
    def _get_cntrno_refno(self):
        for rec in self:
            # Filter out None values before joining
            rec.cntrnos = ', '.join(filter(None, rec.waybillclearinvoicedetail_ids.mapped('cntrno')))
            rec.refnos = ', '.join(filter(None, rec.waybillclearinvoicedetail_ids.mapped('refno')))


class WaybillClearInvoiceDetail(models.Model):
    _name = 'panexlogi.waybill.clearinvoice.detail'
    _description = 'panexlogi.waybill.clearinvoice.detail'

    clearance_type = fields.Many2one('panexlogi.clearance.type', string='Clearance Type')
    cntrno = fields.Char(string='Container No(集装箱号)', tracking=True)
    refno = fields.Char(string='Reference No(参考号)', tracking=True)
    fitem = fields.Many2one('panexlogi.fitems', string='Item(费用项目)', tracking=True)
    fitem_name = fields.Char(string='Item Name(费用项目名称)', related='fitem.name', readonly=True)
    amount = fields.Float(string='Amount（欧元金额）', tracking=True)
    amount_usd = fields.Float(string='Amount（美元金额）', tracking=True)
    poa = fields.Float(string='POA', tracking=True)
    t1 = fields.Float(string='T1', tracking=True)
    vdn = fields.Float(string='VAT defer notification', tracking=True)
    imd = fields.Float(string='Import declaration', tracking=True)
    exa = fields.Float(string='Extra article', tracking=True)
    lfr = fields.Float(string='LFR', tracking=True)
    remark = fields.Text(string='Remark', tracking=True)
    expa = fields.Float(string='Export', tracking=True)
    clearinvoiceinvoiceid = fields.Many2one('panexlogi.waybill.clearinvoice', tracking=True)
