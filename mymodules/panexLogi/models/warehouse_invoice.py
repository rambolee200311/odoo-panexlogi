from odoo import _, models, fields, api
from datetime import timedelta

from odoo.exceptions import UserError


# 外包仓库发票
class WarehouseInvoice(models.Model):
    _name = 'panexlogi.warehouse.invoice'
    _description = 'panexlogi.warehouse.invoice'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = 'billno'

    payee = fields.Many2one('res.partner', string='Payee（收款人）', required=True)
    billno = fields.Char(string='Warehouse Invoice No', readonly=True)
    invno = fields.Char(string='Invoice No（发票号）', required=True,
                        tracking=True)
    date = fields.Date(string='Issue Date（发票日期）', required=True,
                       tracking=True)
    due_date = fields.Date(string='Due Date（到期日）', required=True,
                           tracking=True)
    usdtotal = fields.Float(string='Total_of_USD', store=True,
                            tracking=True, compute='_compute_total')
    eurtotal = fields.Float(string='Total_of_EUR', store=True,
                            tracking=True, compute='_compute_total')
    vat = fields.Float(string='VAT（欧元税额）',
                       tracking=True)
    vat_usd = fields.Float(string='VAT（美元税额）',
                           tracking=True)
    tax_rate = fields.Float(string='Tax Rate')
    pdffile = fields.Binary(string='File（原件）')
    pdffilename = fields.Char(string='File name')
    project = fields.Many2one('panexlogi.project', string='Project（项目）')
    color = fields.Integer()
    state = fields.Selection(
        selection=[
            ('new', 'New'),
            ('confirm', 'Confirm'),
            ('cancel', 'Cancel'),
            ('apply', 'Apply Pay'),
        ],
        default='new',
        string="State",
        tracking=True
    )
    remark = fields.Text(string='Remark')
    warehouseinvoicedetailids = fields.One2many('panexlogi.warehouse.invoice.detail', 'warehouseinvoiceid',
                                                string='Invoice Detail')

    @api.model
    def create(self, values):
        """
        生成仓库发票号
        """
        times = fields.Date.today()
        values['billno'] = self.env['ir.sequence'].next_by_code('seq.warehouse.invoice', times)
        return super(WarehouseInvoice, self).create(values)

    def action_confirm_order(self):
        # 审核
        for rec in self:
            if rec.state != 'new':
                raise UserError(_("You only can confirm New Order"))
            else:
                rec.state = 'confirm'
                return True

    def action_unconfirm_order(self):
        # 弃审
        for rec in self:
            if rec.state != 'confirm':
                raise UserError(_("You only can unconfirm Confirmed Order"))
            else:
                rec.state = 'new'
                return True

    def action_cancel_order(self):
        # 取消
        for rec in self:
            if rec.state != 'new':
                raise UserError(_("You only can cancel New Order"))
            else:
                rec.state = 'cancel'
                return True

    def unlink(self):
        """
        删除
        """
        for record in self:
            if record.state not in ['cancel']:
                raise UserError(_('Only the cancled Invoice can be deleted!'))
        # 删除明细
        self.env['panexlogi.warehouse.invoice.detail'].search([('warehouseinvoiceid', 'in', self.ids)]).unlink()
        # 删除附件
        return super(WarehouseInvoice, self).unlink()

    @api.depends('warehouseinvoicedetailids')
    def _compute_total(self):
        for rec in self:
            rec.eurtotal = sum(rec.warehouseinvoicedetailids.mapped('amount'))
            rec.usdtotal = sum(rec.warehouseinvoicedetailids.mapped('amount_usd'))

        # Create PaymentApplication

    def create_payment_application(self):
        # check if state is confirm
        if self.state != 'confirm':
            raise UserError(_("You can only create Payment Application for a confirmed Delivery Invoice"))
        # Check if PaymentApplication already exists
        domain = [
            ('source', '=', 'Warehouse Invoice')
            , ('source_Code', '=', self.billno)
            , ('state', '!=', 'cancel')
            , ('type', '=', 'import')]

        existing_records = self.env['panexlogi.finance.paymentapplication'].search(domain)
        if existing_records:
            raise UserError(_('Payment Application already exists for this Transport Invoice'))

        for record in self:
            # Create PaymentApplication
            payment_application = self.env['panexlogi.finance.paymentapplication'].create({
                'date': fields.Date.today(),
                'type': 'import',
                'source': 'Warehouse Invoice',
                'payee': record.payee.id,
                'source_Code': record.billno,
                'pdffile': record.pdffile,
                'pdffilename': record.pdffilename,
                'invoiceno': record.invno,
                'invoice_date': record.date,
                'due_date': record.due_date,
            })
            # Unit price= OUD
            for records in self.warehouseinvoicedetailids:
                self.env['panexlogi.finance.paymentapplicationline'].create({
                    'payapp_billno': payment_application.id,
                    'fitem': records.fitem.id,
                    'amount': records.amount,
                    'amount_usd': records.amount_usd,
                    'remark': records.cntrno,
                })

            self.env['panexlogi.finance.paymentapplicationline'].create({
                'payapp_billno': payment_application.id,
                'fitem': self.env['panexlogi.fitems'].search([('code', '=', 'WAH')]).id,
                'amount': record.vat,
                'amount_usd': record.vat_usd,
                'remark': 'VAT-' + str(record.tax_rate) + '%',
            })
            # 修改状态
            record.state = 'apply'
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


# 外包仓库发票明细
class WarehouseInvoiceDetail(models.Model):
    _name = 'panexlogi.warehouse.invoice.detail'
    _description = 'panexlogi.warehouse.invoice.detail'

    fitem = fields.Many2one('panexlogi.fitems', string='Item(费用项目)', tracking=True)
    fitem_name = fields.Char(string='Item Name(费用项目名称)', related='fitem.name', readonly=True)
    amount = fields.Float(string='Amount（欧元金额）')
    amount_usd = fields.Float(string='Amount（美元金额）')
    vat = fields.Float(string='VAT（欧元税额）')
    vat_usd = fields.Float(string='VAT（美元税额）')
    project = fields.Many2one('panexlogi.project', string='Project（项目）')
    waybillno = fields.Char(string='BL')
    cntrno = fields.Char(string='Container')
    cntrnum = fields.Integer(string='Contrainer Num', default=1)
    pallets = fields.Float(string='Pallets', default=26)
    pcs = fields.Float(string='Pallets', default=1)
    remark = fields.Text(string='Remark', tracking=True)
    warehouseinvoiceid = fields.Many2one('panexlogi.warehouse.invoice', string='Warehouse invoice')
    be_bonded = fields.Boolean(string='Be Bonded')
