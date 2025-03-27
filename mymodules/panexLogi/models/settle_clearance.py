from odoo import _, models, fields, api, exceptions
from odoo.exceptions import UserError


# settle shipping
class SettleClearance(models.Model):
    _name = 'panexlogi.settle.clearance'
    _description = 'panexlogi.settle.clearance'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = 'billno'

    billno = fields.Char(string='Bill No')
    period = fields.Many2one('panexlogi.periods', string='Period', required=True)
    start_date = fields.Date(string='Start Date', required=True)
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
            # 条件: project=project, state in confirm,apply,paid, date>=start_date, date<=end_date
            domain = [('waybill_billno.project', '=', rec.project.id),
                      ('state', 'in', ['confirm', 'apply', 'paid']),
                      '&',
                      ('date', '>=', rec.start_date),  # ShipInvoice's date
                      ('date', '<=', rec.end_date)]
            clearance_invoices = self.env['panexlogi.waybill.clearinvoice'].search(domain)
            if clearance_invoices:
                # user confirm to unlink all the details
                rec.settle_clearance_detail_ids.unlink()
                settle_clearance_detail = []
                rec.settle_clearance_detail_ids = False
                for invoice in clearance_invoices:
                    cntrnos = ','.join([str(x) for x in invoice.waybill_billno.details_ids.mapped('cntrno')])
                    cntrqty = len(invoice.waybill_billno.details_ids.mapped('cntrno'))
                    settle_clearance_detail.append((0, 0, {
                        'jobno': invoice.waybill_billno.docno,
                        'invoice_id': invoice.id,
                        'invoiceno': invoice.invno,
                        'waybill_id': invoice.waybill_billno.id,
                        'waybillno': invoice.waybill_billno.waybillno,
                        'Container': cntrnos,
                        'container_qty': cntrqty,
                        'poa': invoice.poa,
                        't1': invoice.t1,
                        'vdn': invoice.vdn,
                        'imd': invoice.imd,
                        'exa': invoice.exa,
                        'lfr': invoice.lfr,
                        'invoice_amount': invoice.eurtotal,
                        'remark': invoice.desc,
                    }))
                rec.settle_clearance_detail_ids = settle_clearance_detail


class SettleClearanceDetail(models.Model):
    _name = 'panexlogi.settle.clearance.detail'
    _description = 'panexlogi.settle.clearance.detail'

    settle_clearance_id = fields.Many2one('panexlogi.settle.clearance', string='Settle Clearance')
    jobno = fields.Char(string='Job No')
    invoice_id = fields.Many2one('panexlogi.waybill.clearinvoice', string='Invoice ID')
    invoiceno = fields.Char(string='Invoice No')
    waybill_id = fields.Many2one('panexlogi.waybill', string='Waybill ID')
    waybillno = fields.Char(string='BL No')
    Container = fields.Char(string='Container')
    container_qty = fields.Char(string='Container Quantity')
    fitem = fields.Many2one('panexlogi.fitems', string='Item(费用项目)', tracking=True)
    fitem_name = fields.Char(string='Item Name(费用项目名称)', related='fitem.name', readonly=True)
    poa = fields.Float(string='POA', tracking=True)
    t1 = fields.Float(string='T1', tracking=True, default=0)
    vdn = fields.Float(string='VAT defer notification', tracking=True, default=0)
    imd = fields.Float(string='Import declaration', tracking=True, default=0)
    exa = fields.Float(string='Extra article', tracking=True, default=0)
    lfr = fields.Float(string='LFR', tracking=True, default=0)
    amount = fields.Float(string='Amount（欧元金额）', compute='get_total_amount', store=True)
    invoice_amount = fields.Float(string='Invoice Amount', tracking=True)
    remark = fields.Text(string='Remark', tracking=True)

    @api.depends('poa', 't1', 'vdn', 'imd', 'exa', 'lfr')
    def get_total_amount(self):
        amount = 0
        for rec in self:
            amount += rec.poa + rec.t1 + rec.vdn + rec.imd + rec.exa + rec.lfr
            rec.amount = amount
