from odoo import _, models, fields, api, exceptions
from odoo.exceptions import UserError
import json


class TransportInvoice(models.Model):
    _name = 'panexlogi.transport.invoice'
    _description = 'panexlogi.transport.invoice'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = 'billno'

    billno = fields.Char(string='BillNo', readonly=True)
    date = fields.Date(string='Invoice Date', default=fields.Date.today)
    due_date = fields.Date(string='Due Date')
    truckco = fields.Many2one('res.partner', string='Truck Co（卡车公司）', domain=[('truck', '=', 'True')])
    truckco_code = fields.Char(string='Truck Co Code', related='truckco.panex_code', readonly=True)
    fitem = fields.Many2one('panexlogi.fitems', string='Charge Item')
    fitem_name = fields.Char(string='Charge Item Name', related='fitem.name', readonly=True)

    invoiceno = fields.Char(string='Invoice No')
    amount = fields.Float(string='Amount')
    remark = fields.Text(string='Remark')
    check_message = fields.Text(string='Check Message')
    state = fields.Selection(
        selection=[
            ('new', 'New'),
            ('confirm', 'Confirm'),
            ('received', 'Received'),
            ('cancel', 'Cancel'),
        ],
        default='new',
        string="Status",
        tracking=True
    )
    pdffile = fields.Binary(string='File（原件）')
    pdffilename = fields.Char(string='File name')
    transportinvoicedetailids = fields.One2many('panexlogi.transport.invoice.detail', 'transportinvoiceid',
                                                string='Details')

    transportinvoicedetail_json = fields.Text(string='Transport Invoice Details JSON',
                                              compute='_compute_transportinvoicedetail_json',
                                              inverse='_set_transportinvoicedetail_json')

    allow_notunique = fields.Boolean(string='Allow Not Unique', default=False)
    reason_notunique = fields.Text(string='Reason Not Unique')

    @api.depends('transportinvoicedetailids')
    def _compute_transportinvoicedetail_json(self):
        for record in self:
            details = []
            for detail in record.transportinvoicedetailids:
                details.append({
                    'waybillno': detail.waybillno,
                    'cntrno': detail.cntrno,
                    'collterminal_name': detail.collterminal_name,
                    'dropterminal_name': detail.dropterminal_name,
                    'unlolocation': detail.unlolocation,
                    'unitprice': detail.unitprice,
                    'surcharge': detail.surcharge,
                    'adrcharge': detail.adrcharge,
                    'waithours': detail.waithours,
                    'diselcharge': detail.dieselcharge,
                    'extrahours': detail.extrahours,
                    'remark': detail.remark,
                })
            record.transportinvoicedetail_json = json.dumps(details)

    def _set_transportinvoicedetail_json(self):
        for record in self:
            details = json.loads(record.transportinvoicedetail_json)
            record.transportinvoicedetailids = [(5, 0, 0)]  # Clear existing details
            for detail in details:
                record.transportinvoicedetailids = [(0, 0, {
                    'cntrno': detail['cntrno'],
                    'collterminal_name': detail['collterminal_name'],
                    'dropterminal_name': detail['dropterminal_name'],
                    'unlolocation': detail['unlolocation'],
                    'unitprice': detail['unitprice'],
                    'surcharge': detail['surcharge'],
                    'adrcharge': detail['adrcharge'],
                    'waithours': detail['waithours'],
                    'diselcharge': detail['diselcharge'],
                    'extrahours': detail['extrahours'],
                    'remark': detail['remark'],
                })]

    @api.model
    def create(self, values):
        """
        生成跟踪单号
        """
        times = fields.Date.today()
        values['billno'] = self.env['ir.sequence'].next_by_code('seq.transport.invoice', times)
        values['state'] = 'new'
        return super(TransportInvoice, self).create(values)

    def action_confirm_order(self):

        for rec in self:
            valid = True
            if rec.state != 'new':
                valid = False
                raise UserError(_("You only can confirm New Invoice"))
            else:
                if not rec.transportinvoicedetailids:
                    valid = False
                    raise UserError(_("You must have at least one detail line"))
                # check waybillno cntrno valid
                for detail in rec.transportinvoicedetailids:
                    waybillno = detail.waybillno
                    billno = 0
                    waybill_record = self.env['panexlogi.waybill'].search([('waybillno', '=', waybillno)])
                    if not waybill_record:
                        detail.check = False
                        detail.check_message = 'waybillno not exist'
                    else:
                        detail.project = waybill_record[0].project
                        billno = waybill_record[0].id

                    cntrno = detail.cntrno
                    domain = [
                        ('transportorderid.waybill_billno', '=', billno),
                        ('cntrno', '=', cntrno),
                    ]
                    existing_records = self.env['panexlogi.transport.order.detail'].search(domain)
                    if not existing_records:
                        detail.check = False
                        detail.check_message = 'waybillno and cntrno not exist'
                    else:
                        truckco = rec.truckco
                        domain = [
                            ('transportorderid.truckco', '=', truckco.id),
                            ('transportorderid.state', '!=', 'cancel'),
                        ]
                        existing_records2 = existing_records.search(domain)
                        if not existing_records2:
                            detail.check = False
                            detail.check_message = 'waybillno and cntrno exist, but truckco not exist'
                        else:
                            detail.check = True
                            detail.check_message = ''
            # final check
            for detail in rec.transportinvoicedetailids:
                if not detail.check:
                    valid = False
                    rec.check_message = 'Check failed, detail has invalid data'
                    break
            if valid:
                rec.check_message = ''
                rec.state = 'confirm'
                return True

    def action_unconfirm_order(self):
        for rec in self:
            if rec.state != 'confirm':
                raise UserError(_("You only can unconfirm Confirmed Invoice"))
            else:
                rec.state = 'new'
                return True

    def action_cancel_order(self):
        for rec in self:
            if rec.state != 'new':
                raise UserError(_("You only can cancel New Invoice"))
            else:
                rec.state = 'cancel'
                return True

    # Create PaymentApplication
    def create_payment_application(self):
        # check if state is confirm
        if self.state != 'confirm':
            raise UserError(_("You can only create Payment Application for a confirmed Transport Invoice"))
        # Check if PaymentApplication already exists
        domain = [
            ('source', '=', 'Transport Invoice')
            , ('source_Code', '=', self.billno)
            , ('state', '!=', 'cancel')
            , ('type', '=', 'trucking')]

        existing_records = self.env['panexlogi.finance.paymentapplication'].search(domain)
        if existing_records:
            raise UserError(_('Payment Application already exists for this Transport Invoice'))

        for record in self:
            # Create PaymentApplication
            payment_application = self.env['panexlogi.finance.paymentapplication'].create({
                'date': fields.Date.today(),
                'type': 'trucking',
                'source': 'Transport Invoice',
                'payee': record.truckco.id,
                'source_Code': record.billno,
                'pdffile': record.pdffile,
                'pdffilename': record.pdffilename,
                'invoiceno': record.invoiceno,
                'invoice_date': record.date,
                'due_date': record.due_date,
            })
            # Unit price= INT
            for records in record.transportinvoicedetailids:
                # Create PaymentApplicationLine
                if records.unitprice != 0:
                    self.env['panexlogi.finance.paymentapplicationline'].create({
                        'fitem': self.env['panexlogi.fitems'].search([('code', '=', 'INT')]).id,
                        'payapp_billno': payment_application.id,
                        'amount': records.unitprice,
                        'remark': records.remark,
                        'project': records.project.id,
                    })
                # ADR Surcharge= ADR
                if records.adrcharge != 0:
                    self.env['panexlogi.finance.paymentapplicationline'].create({
                        'invoiceno': record.invoiceno,
                        'invoice_date': record.date,
                        'due_date': record.due_date,
                        'fitem': self.env['panexlogi.fitems'].search([('code', '=', 'ADR')]).id,
                        'payapp_billno': payment_application.id,
                        'amount': records.adrcharge,
                        'remark': records.remark,
                        'project': records.project.id,
                    })
                # Wait Hours= WAI
                if records.waithours != 0:
                    self.env['panexlogi.finance.paymentapplicationline'].create({
                        'invoiceno': record.invoiceno,
                        'invoice_date': record.date,
                        'due_date': record.due_date,
                        'fitem': self.env['panexlogi.fitems'].search([('code', '=', 'WAI')]).id,
                        'payapp_billno': payment_application.id,
                        'amount': records.waithours,
                        'remark': records.remark,
                        'project': records.project.id,
                    })
                # Terminal Surcharge= TSU
                if records.surcharge != 0:
                    self.env['panexlogi.finance.paymentapplicationline'].create({
                        'invoiceno': record.invoiceno,
                        'invoice_date': record.date,
                        'due_date': record.due_date,
                        'fitem': self.env['panexlogi.fitems'].search([('code', '=', 'TSU')]).id,
                        'payapp_billno': payment_application.id,
                        'amount': records.surcharge,
                        'remark': records.remark,
                        'project': records.project.id,
                    })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': 'Trucking Payment Application create successfully!',
                'type': 'success',
                'sticky': False,
            }
        }

    # Auto calculate amount
    @api.onchange('transportinvoicedetailids.unitprice',
                  'transportinvoicedetailids.surcharge',
                  'transportinvoicedetailids.waithours',
                  'transportinvoicedetailids.extrahours',
                  'transportinvoicedetailids.adrcharge',
                  'transportinvoicedetailids.dieselcharge')
    def _onchange_amount(self):
        for record in self:
            record.amount = 0
            sum_amount = 0
            for detail in record.transportinvoicedetailids:
                sum_amount += detail.unitprice + detail.surcharge + detail.waithours + detail.extrahours + detail.adrcharge + detail.dieselcharge
            record.amount = sum_amount




class TransportInvoiceDetail(models.Model):
    _name = 'panexlogi.transport.invoice.detail'
    _description = 'panexlogi.transport.invoice.detail'

    waybillno = fields.Char(string='BL')
    cntrno = fields.Char(string='Container')
    collterminal_name = fields.Char(string='Collection Terminal')
    dropterminal_name = fields.Char(string='Drop-off Terminal')
    unlolocation = fields.Char(string='Unloaded Location')
    unitprice = fields.Float(string='Unit Price')
    surcharge = fields.Float(string='Terminal Surcharge')
    adrcharge = fields.Float(string='ADR Charge')
    waithours = fields.Integer(string='Waiting Hours Free')
    dieselcharge = fields.Float(string='Diesel')
    extrahours = fields.Float(string='Extra Hours')
    remark = fields.Text(string='Remark')

    project = fields.Many2one('panexlogi.project', string='Project（项目）', tracking=True)
    check = fields.Boolean(string='Check with Order')
    check_message = fields.Text(string='Check Message')
    warehouse = fields.Many2one('stock.warehouse', string='Unloaded Warehouse')
    warehouse_code = fields.Char(string='Warehouse Code', related='warehouse.code', readonly=True)
    dropterminal = fields.Many2one('panexlogi.terminal', string='Empty Container Drop-off Terminal')
    dropterminal_code = fields.Char(string='Drop-off Terminal Code', related='dropterminal.terminal_code',
                                    readonly=True)
    collterminal = fields.Many2one('panexlogi.terminal', string='Collection Terminal')
    collterminal_code = fields.Char(string='Collection Terminal Code', related='collterminal.terminal_code',
                                    readonly=True)
    unlodate = fields.Date(string='Unloaded Date')

    transportinvoiceid = fields.Many2one('panexlogi.transport.invoice', string='Transport Invoice')

    # check waybillno cntrno unique
    @api.constrains('waybillno', 'cntrno')
    def _check_waybillno_id(self):
        for r in self:
            # when allow_notunique is True, skip the check
            # when not unique, raise error
            if not r.transportinvoiceid.allow_notunique:
                domain = [
                    ('waybillno', '=', r.waybillno),
                    ('cntrno', '=', r.cntrno),
                    ('transportinvoiceid.truckco', '=', r.transportinvoiceid.truckco.id),
                    ('transportinvoiceid.state', '!=', 'cancel'),
                    ('id', '!=', r.id),
                ]
                existing_records = self.search(domain)
                if existing_records:
                    raise UserError(_('bl&container must be unique'))
