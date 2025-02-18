from odoo import _, models, fields, api, exceptions
from odoo.exceptions import UserError
from odoo.tools import json


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

    @api.depends('transportinvoicedetailids')
    def _compute_transportinvoicedetail_json(self):
        for record in self:
            details = []
            for detail in record.transportinvoicedetailids:
                details.append({
                    'cntrno': detail.cntrno,
                    'collterminal': detail.collterminal.id,
                    'warehouse': detail.warehouse.id,
                    'unlolocation': detail.unlolocation,
                    'unlodate': detail.unlodate,
                    'dropterminal': detail.dropterminal.id,
                    'unitprice': detail.unitprice,
                    'surcharge': detail.surcharge,
                    'waithours': detail.waithours,
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
                    'collterminal': detail['collterminal'],
                    'warehouse': detail['warehouse'],
                    'unlolocation': detail['unlolocation'],
                    'unlodate': detail['unlodate'],
                    'dropterminal': detail['dropterminal'],
                    'unitprice': detail['unitprice'],
                    'surcharge': detail['surcharge'],
                    'waithours': detail['waithours'],
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
