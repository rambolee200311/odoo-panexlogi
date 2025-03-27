from odoo import _, models, fields, api, exceptions
from odoo.exceptions import UserError


# settle shipping
class SettleShipping(models.Model):
    _name = 'panexlogi.settle.shipping'
    _description = 'panexlogi.settle.shipping'
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
    total_amount_usd = fields.Float(string='Total Amount USD', compute='get_total_amount', store=True)
    settle_shipping_detail_ids = fields.One2many('panexlogi.settle.shipping.detail', 'settle_shipping_id')

    @api.model
    def create(self, values):
        """
        生成跟踪单号
        """
        times = fields.Date.today()
        values['billno'] = self.env['ir.sequence'].next_by_code('seq.settle.shipping', times)
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

    # get shipping invoice detail
    def get_shipping_detail(self):
        for rec in self:
            # 条件: project=project, state in confirm,apply,paid, date>=start_date, date<=end_date
            domain = [('waybill_billno.project', '=', rec.project.id),
                      ('state', 'in', ['confirm', 'apply', 'paid']),
                      '&',
                      ('date', '>=', rec.start_date),  # ShipInvoice's date
                      ('date', '<=', rec.end_date)]
            shipping_invoices = self.env['panexlogi.waybill.shipinvoice'].search(domain)
            if shipping_invoices:
                # user confirm to unlink all the details
                rec.settle_shipping_detail_ids.unlink()
                settle_shipping_detail = []
                rec.settle_shipping_detail_ids = False
                for invoice in shipping_invoices:
                    cntrnos = ','.join([str(x) for x in invoice.waybill_billno.details_ids.mapped('cntrno')])
                    cntrqty = len(invoice.waybill_billno.details_ids.mapped('cntrno'))
                    for line_detail in invoice.waybillshipinvoicedetail_ids:
                        settle_shipping_detail.append((0, 0, {
                            'jobno': invoice.waybill_billno.docno,
                            'invoice_id': invoice.id,
                            'invoiceno': invoice.invno,
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


class SettleShippingDetail(models.Model):
    _name = 'panexlogi.settle.shipping.detail'
    _description = 'panexlogi.settle.shipping.detail'

    jobno = fields.Char(string='Job No')
    invoice_id = fields.Many2one('panexlogi.waybill.shipinvoice', string='Invoice ID')
    invoiceno = fields.Char(string='Invoice No')
    waybill_id = fields.Many2one('panexlogi.waybill', string='Waybill ID')
    waybillno = fields.Char(string='BL No')
    Container = fields.Char(string='Container')
    shipping = fields.Many2one('res.partner', string='Shipping Line')
    container_qty = fields.Char(string='Container Quantity')
    fitem = fields.Many2one('panexlogi.fitems', string='Item(费用项目)', tracking=True)
    fitem_name = fields.Char(string='Item Name(费用项目名称)', related='fitem.name', readonly=True)
    amount = fields.Float(string='Amount（欧元金额）', tracking=True)
    amount_usd = fields.Float(string='Amount（美元金额）', tracking=True)
    remark = fields.Text(string='Remark', tracking=True)

    settle_shipping_id = fields.Many2one('panexlogi.settle.shipping', string='Settle Shipping')
