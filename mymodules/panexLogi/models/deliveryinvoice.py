from odoo import _, models, fields, api, exceptions
from odoo.exceptions import UserError
import json

"""
delivery invoice
"""


class DeliveryInvoice(models.Model):
    _name = 'panexlogi.delivery.invoice'
    _description = 'panexlogi.delivery.invoice'
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
    amount = fields.Float(string='Amount EUR', compute='_onchange_amount', store=True)
    amount_usd = fields.Float(string='Amount USD', compute='_onchange_amount_usd', store=True)
    tax = fields.Float(string='Tax')
    tax_usd = fields.Float(string='Tax USD')
    tax_rate = fields.Float(string='Tax Rate')
    amount_tax = fields.Float(string='Amount Tax', compute='_onchange_amount_tax', store=True)
    amount_tax_usd = fields.Float(string='Amount Tax USD', compute='_onchange_amount_tax', store=True)
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
    deliveryinvoicedetailids = fields.One2many('panexlogi.delivery.invoice.detail', 'deleveryinvoiceid',
                                               string='Delivery Invoice Detail')
    check_message = fields.Text(string='Check Message')

    @api.model
    def create(self, values):
        """
        生成跟踪单号
        """
        times = fields.Date.today()
        values['billno'] = self.env['ir.sequence'].next_by_code('seq.delivery.invoice', times)
        values['state'] = 'new'
        return super(DeliveryInvoice, self).create(values)

    """
    @api.model
    def write(self, values):
        result = super(DeliveryInvoice, self).write(values)
        for record in self:
            amount = 0
            amount_usd = 0
            amount_tax = 0
            amount_tax_usd = 0
            for res in record.deliveryinvoice_detail_ids:
                amount += res.amount
                amount_usd += res.amount_usd

            amount_tax = amount + record.tax
            amount_tax_usd = amount_usd + record.tax_usd
            record.update({
                'amount': amount,
                'amount_usd': amount_usd,
                'amount_tax': amount_tax,
                'amount_tax_usd': amount_tax_usd
            })

        return result
    """

    def unlink(self):
        """
        删除
        """
        for record in self:
            if record.state not in ['cancel']:
                raise UserError(_('Only the cancled Invoice can be deleted!'))
        # 删除明细
        self.env['panexlogi.delivery.invoice.detail'].search([('deleveryinvoiceid', 'in', self.ids)]).unlink()
        # 删除附件
        return super(DeliveryInvoice, self).unlink()

    def action_confirm_order(self):
        """
        确认
        """
        if self.state == 'new':

            # check combination of truckco and inner ref is exist in delivery order,and write check_message ,check is false
            for record in self.deliveryinvoicedetailids:
                domain = [('trucker', '=', self.truckco.id), ('inner_ref', '=', record.inner_ref)]
                if self.env['panexlogi.delivery'].search_count(domain) == 0:
                    record.check = False
                    record.check_message = 'The combination of truck company and inner ref is not exist in delivery order!'
                    self.check_message = 'The combination of truck company and inner ref is not exist in delivery order!'
                    raise exceptions.ValidationError(
                        _('The combination of truck company and inner ref is not exist in delivery order!'))
                else:
                    record.check = True
                    record.check_message = ''

            self.check_message = ''
            self.state = 'confirm'

        else:
            raise UserError(_('The status of the current Invoice is not new!'))

    def action_received_order(self):
        """
        收到
        """
        if self.state == 'confirm':
            self.state = 'received'
        else:
            raise UserError(_('The status of the current Invoice is not confirm!'))

    def action_cancel_order(self):
        """
        取消
        """
        if self.state == 'new':
            self.state = 'cancel'
        else:
            raise UserError(_('The status of the current Invoice is not new!'))

    def action_unconfirm_order(self):
        """
        取消确认
        """
        if self.state == 'confirm':
            self.state = 'new'
        else:
            raise UserError(_('The status of the current Invoice is not confirm!'))

    def action_unreceived_order(self):
        """
        取消收到
        """
        if self.state == 'received':
            self.state = 'confirm'
        else:
            raise UserError(_('The status of the current Invoice is not received!'))

    @api.depends('deliveryinvoicedetailids.amount')
    def _onchange_amount(self):
        """
        计算不含税金额
        """
        for r in self:
            amount = 0
            for rs in r.deliveryinvoicedetailids:
                amount += rs.amount
            r.amount = amount
            print(f"Amount calculated: {amount}")  # Debugging statement

    @api.depends('deliveryinvoicedetailids.amount_usd')
    def _onchange_amount_usd(self):
        """
        计算不含税金额
        """
        for r in self:
            amount = 0
            for rs in r.deliveryinvoicedetailids:
                amount += rs.amount_usd
            r.amount_usd = amount
            print(f"Amount calculated: {amount}")  # Debugging statement

    @api.depends('amount', 'tax', 'amount_usd', 'tax_usd')
    def _onchange_amount_tax(self):
        """
        计算含税金额
        """
        for r in self:
            r.amount_tax = r.amount + r.tax
            r.amount_tax_usd = r.amount_usd + r.tax_usd


class DeliveryInvoiceDetail(models.Model):
    _name = 'panexlogi.delivery.invoice.detail'
    _description = 'panexlogi.delivery.invoice.detail'

    date_order_no = fields.Char(string='Date Order No')
    destinations_comments = fields.Text(string='Destinations Comments')
    inner_ref = fields.Char(string='Inner Ref')
    waybillno = fields.Char(string='BL')
    cntrno = fields.Char(string='Container')
    rates = fields.Float(string='Rates')
    deleveryinvoiceid = fields.Many2one('panexlogi.delivery.invoice', string='Delivery Invoice')
    amount = fields.Float(string='Amount EUR')
    amount_usd = fields.Float(string='Amount USD')
    tax = fields.Float(string='Tax')
    tax_usd = fields.Float(string='Tax USD')
    amount_tax = fields.Float(string='Amount Tax')
    amount_tax_usd = fields.Float(string='Amount Tax USD')
    check = fields.Boolean(string='Check with Order')
    check_message = fields.Text(string='Check Message')

    # chcek inner ref is unique,and state is not cancel

    @api.constrains('inner_ref')
    def _check_inner_ref(self):
        for record in self:
            if record.inner_ref:
                domain = [('inner_ref', '=', record.inner_ref), ('deleveryinvoiceid.state', '!=', 'cancel')]
                if self.search_count(domain) > 1:
                    raise exceptions.ValidationError(_('The inner ref must be unique!'))
