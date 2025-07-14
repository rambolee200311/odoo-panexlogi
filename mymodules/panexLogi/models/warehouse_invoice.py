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

        domain2 = [
            ('source', '=', 'Warehouse Invoice')
            , ('payee', '=', self.payee.id)
            , ('invoiceno', '=', self.invno)
            , ('state', '!=', 'cancel')]
        existing_records = self.env['panexlogi.finance.paymentapplication'].search(domain2)
        if existing_records:
            existing_billnos = ", ".join(existing_records.mapped('billno'))
            raise UserError(_(
                "Invoice No '%(invno)s' is already used in Payment Application(s) [%(billnos)s] '."
            ) % {
                                'invno': self.invno,
                                'billnos': existing_billnos
                            })

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
            project = False
            for records in self.warehouseinvoicedetailids:
                if records.project:
                    project = records.project.id
                else:
                    if record.project:
                        project = record.project.id
                self.env['panexlogi.finance.paymentapplicationline'].create({
                    'payapp_billno': payment_application.id,
                    'fitem': records.fitem.id,
                    'amount': records.amount,
                    'amount_usd': records.amount_usd,
                    'remark': records.cntrno,
                    'project': project,
                })

            if record.vat or record.vat_usd:
                if record.vat != 0 or record.vat_usd != 0:
                    self.env['panexlogi.finance.paymentapplicationline'].create({
                        'payapp_billno': payment_application.id,
                        'fitem': self.env['panexlogi.fitems'].search([('code', '=', 'WAH')]).id,
                        'amount': record.vat,
                        'amount_usd': record.vat_usd,
                        'remark': 'VAT-' + str(record.tax_rate) + '%',
                        'project': project,
                    })
            # 修改状态
            record.state = 'apply'

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

    # split the waybill into containers
    def split_waybill(self):
        # check if waybillno is already in the warehouse invoice
        try:
            for rec in self:
                for record in rec.warehouseinvoicedetailids:
                    if record.waybillno and not record.cntrno:
                        cntrno_qty = 0
                        domain = [('waybill_billno.waybillno', '=', record.waybillno),
                                  ('waybill_billno.state', 'in', ['new', 'confirm'])]
                        waybill_details = self.env['panexlogi.waybill.details'].search(domain)
                        if waybill_details:
                            cntrno_qty = len(set(waybill_details.mapped('cntrno')))

                        # split the waybill into containers,delete the waybill details
                        if cntrno_qty >= 1:
                            # Calculate the total of the first 6 parts
                            amount_per_cntr = round(record.amount / cntrno_qty, 2)
                            amount_per_cntr_usd = round(record.amount_usd / cntrno_qty, 2)
                            vat_per_cntr = round(record.vat / cntrno_qty, 2)
                            vat_per_cntr_usd = round(record.vat_usd, 2)
                            # Calculate the total of the first 6 parts
                            total_amount_first_6 = amount_per_cntr * (cntrno_qty - 1)
                            total_amount_usd_first_6 = amount_per_cntr_usd * (cntrno_qty - 1)
                            total_vat_first_6 = vat_per_cntr * (cntrno_qty - 1)
                            total_vat_usd_first_6 = vat_per_cntr_usd * (cntrno_qty - 1)
                            # Calculate the remainder for the last part
                            amount_last_part = record.amount - total_amount_first_6
                            amount_usd_last_part = record.amount_usd - total_amount_usd_first_6
                            vat_last_part = record.vat - total_vat_first_6
                            vat_usd_last_part = record.vat_usd - total_vat_usd_first_6
                            sequence = 1
                            for waybill_detail in waybill_details:
                                if sequence < cntrno_qty:
                                    amount = amount_per_cntr
                                    amount_usd = amount_per_cntr_usd
                                    vat = vat_per_cntr
                                    vat_usd = vat_per_cntr_usd
                                else:
                                    amount = amount_last_part
                                    amount_usd = amount_usd_last_part
                                    vat = vat_last_part
                                    vat_usd = vat_usd_last_part
                                # write the amount to the warehouse invoice detail
                                if sequence == 1:
                                    record.amount = amount
                                    record.amount_usd = amount_usd
                                    record.vat = vat
                                    record.vat_usd = vat_usd
                                    record.cntrno = waybill_detail.cntrno
                                    record.cntrnum = 1
                                    record.pallets = waybill_detail.pallets
                                    record.pcs = waybill_detail.pcs
                                    record.remark = record.remark
                                else:
                                    # create a new warehouse invoice detail
                                    self.env['panexlogi.warehouse.invoice.detail'].create({
                                        'fitem': record.fitem.id,
                                        'amount': amount,
                                        'amount_usd': amount_usd,
                                        'vat': vat,
                                        'vat_usd': vat_usd,
                                        'project': record.project.id,
                                        'waybillno': record.waybillno,
                                        'cntrno': waybill_detail.cntrno,
                                        'cntrnum': 1,
                                        'pallets': waybill_detail.pallets,
                                        'pcs': waybill_detail.pcs,
                                        'remark': record.remark,
                                        'warehouseinvoiceid': rec.id,
                                    })
                                # record.to_delete = True
                                sequence += 1
            # Unlink all warehouseinvoicedetailids where to_delete is True
            # details_to_delete = rec.warehouseinvoicedetailids.filtered(lambda d: d.to_delete)
            # details_to_delete.unlink()
            return True
        except Exception as e:
            raise UserError(_('An error occurred while splitting waybill: %s') % str(e))


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
    pallets = fields.Float(string='pallets', default=26)
    pcs = fields.Float(string='pcs', default=1)
    remark = fields.Text(string='Remark', tracking=True)
    warehouseinvoiceid = fields.Many2one('panexlogi.warehouse.invoice', string='Warehouse invoice')
    be_bonded = fields.Boolean(string='Be Bonded')
    to_delete = fields.Boolean(string='To Delete', default=False)
