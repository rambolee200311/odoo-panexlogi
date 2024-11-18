from odoo import _, models, fields, api, exceptions


class TransportInvoice(models.Model):
    _name = 'panexlogi.transport.invoice'
    _description = 'panexlogi.transport.invoice'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = 'billno'

    billno = fields.Char(string='BillNo', readonly=True)
    date = fields.Date(string='Order Date', default=fields.Date.today)
    due_date = fields.Date(string='Due Date')
    truckco = fields.Many2one('res.partner', string='Truck Co（卡车公司）', domain=[('truck', '=', 'True')])
    truckco_code = fields.Char(string='Truck Co Code', related='truckco.panex_code', readonly=True)
    fitem = fields.Many2one('panexlogi.fitems', string='Charge Item')
    fitem_name = fields.Char(string='Charge Item Name', related='fitem.name', readonly=True)

    invoiceno = fields.Char(string='Invoice No')
    amount = fields.Float(string='Amount')
    remark = fields.Text(string='Remark')

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
    transportinvoicedetailids = fields.One2many('panexlogi.transport.invoice.detail', 'transportinvoiceid',string='Details')
    @api.model
    def create(self, values):
        """
        生成跟踪单号
        """
        times = fields.Date.today()
        values['billno'] = self.env['ir.sequence'].next_by_code('seq.transport.invoice', times)
        values['state'] = 'new'
        return super(TransportInvoice, self).create(values)


class TransportInvoiceDetail(models.Model):
    _name = 'panexlogi.transport.invoice.detail'
    _description = 'panexlogi.transport.invoice.detail'

    cntrno = fields.Char(string='Container NO')
    collterminal = fields.Many2one('panexlogi.terminal', string='Collection Terminal')
    collterminal_code = fields.Char(string='Collection Terminal Code', related='collterminal.terminal_code',
                                    readonly=True)
    warehouse = fields.Many2one('stock.warehouse', string='Unloaded Warehouse')
    warehouse_code = fields.Char(string='Warehouse Code', related='warehouse.code', readonly=True)
    unlolocation = fields.Char(string='Unloaded Location')
    unlodate = fields.Date(string='Unloaded Date')

    dropterminal = fields.Many2one('panexlogi.terminal', string='Empty Container Drop-off Terminal')
    dropterminal_code = fields.Char(string='Drop-off Terminal Code', related='dropterminal.terminal_code',
                                    readonly=True)

    unitprice = fields.Float(string='Unit Price')
    surcharge = fields.Float(string='Terminal Surcharge')
    waithours = fields.Integer(string='Waiting Hours Free')
    extrahours = fields.Float(string='Extra Hours')
    remark = fields.Text(string='Remark')

    transportinvoiceid = fields.Many2one('panexlogi.transport.invoice', string='Transport Invoice')
