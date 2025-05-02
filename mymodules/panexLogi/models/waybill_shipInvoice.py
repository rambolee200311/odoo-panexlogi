from odoo import _, models, fields, api
from datetime import timedelta

from odoo.exceptions import UserError


# 运输发票


class WaybillShipInvoice(models.Model):
    _name = 'panexlogi.waybill.shipinvoice'
    _description = 'panexlogi.waybill.shipinvoice'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = 'billno'

    payee = fields.Many2one('res.partner', string='Payee（收款人）', required=True)
    billno = fields.Char(string='Shipping Invoice No', readonly=True)
    invno = fields.Char(string='Invoice No（发票号）', required=True,
                        tracking=True)
    date = fields.Date(string='Issue Date（发票日期）', required=True,
                       tracking=True)
    due_date = fields.Date(string='Due Date（到期日）', required=True,
                           tracking=True)
    usdtotal = fields.Float(string='Total_of_USD', store=True,
                            tracking=True, compute='_compute_total_usd')
    eurtotal = fields.Float(string='Total_of_EUR', store=True,
                            tracking=True, compute='_compute_total_eur')
    pdffile = fields.Binary(string='File（原件）')
    pdffilename = fields.Char(string='File name')
    waybill_billno = fields.Many2one('panexlogi.waybill',
                                     tracking=True, required=True)
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
    waybillshipinvoicedetail_ids = fields.One2many('panexlogi.waybill.shipinvoice.detail', 'waybillshipinvoiceid')

    @api.model
    def create(self, values):
        """
        generate bill number
        """
        times = fields.Date.today()
        values['billno'] = self.env['ir.sequence'].next_by_code('seq.waybill.shipinvoice', times)
        return super(WaybillShipInvoice, self).create(values)

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

    @api.depends('waybillshipinvoicedetail_ids.amount')
    def _compute_total_eur(self):
        for rec in self:
            rec.eurtotal = 0
            if rec.waybillshipinvoicedetail_ids:
                rec.eurtotal = sum(rec.waybillshipinvoicedetail_ids.mapped('amount'))

    @api.depends('waybillshipinvoicedetail_ids.amount_usd')
    def _compute_total_usd(self):
        for rec in self:
            rec.usdtotal = 0
            if rec.waybillshipinvoicedetail_ids:
                rec.usdtotal = sum(rec.waybillshipinvoicedetail_ids.mapped('amount_usd'))

    # Create PaymentApplication
    def create_payment_application(self):
        # Create PaymentApplication
        for record in self:
            # check if state is confirm
            if record.state != 'confirm':
                raise UserError(_("You can only create Payment Application for a confirmed Shipping Invoice"))
            # Check if PaymentApplication already exists
            direction = record.waybill_billno.direction
            domain1 = [
                ('source', '=', 'Shipping Invoice')
                , ('source_Code', '=', record.billno)
                , ('state', '!=', 'cancel')
                , ('type', '=', direction)]
            existing_records = self.env['panexlogi.finance.paymentapplication'].search(domain1)
            if existing_records:
                raise UserError(_
                                ("Payment Application '%(billno)s' already exists for this Shipping Invoice '%(suorce)s'") %
                                {
                                    'billno': existing_records.billno, 'suorce': record.billno
                                })
            # check if invoiceno is duplicate
            domain2 = [
                ('source', '=', 'Shipping Invoice')
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
                'source': 'Shipping Invoice',
                'payee': record.payee.id,
                'source_Code': record.billno,
                'pdffile': record.pdffile,
                'pdffilename': record.pdffilename,
                'invoiceno': record.invno,
                'invoice_date': record.date,
                'due_date': record.due_date,
                'waybill_billno': record.waybill_billno.id,
                'shipinvoice_id': record.id
            })
            for records in record.waybillshipinvoicedetail_ids:
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
                ('source', '=', 'Shipping Invoice'),
                ('source_Code', '=', record.billno),
                ('state', '!=', 'cancel'),
                ('type', '=', 'import')
            ]
            existing_records = self.env['panexlogi.finance.paymentapplication'].search(domain)
            if existing_records:
                raise UserError(_('You cannot delete a Shipping Invoice that has a Payment Application.'))
        return super(WaybillShipInvoice, self).unlink()

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


class WaybillShipInvoiceDetail(models.Model):
    _name = 'panexlogi.waybill.shipinvoice.detail'
    _description = 'panexlogi.waybill.shipinvoice.detail'

    fitem = fields.Many2one('panexlogi.fitems', string='Item(费用项目)', tracking=True)
    fitem_name = fields.Char(string='Item Name(费用项目名称)', related='fitem.name', readonly=True)
    amount = fields.Float(string='Amount（欧元金额）', tracking=True)
    amount_usd = fields.Float(string='Amount（美元金额）', tracking=True)
    remark = fields.Text(string='Remark', tracking=True)
    waybillshipinvoiceid = fields.Many2one('panexlogi.waybill.shipinvoice', tracking=True)
