from datetime import datetime, timedelta
import pytz

from odoo import _, models, fields, api
from odoo.exceptions import UserError


# 提单
class Waybill(models.Model):
    _name = 'panexlogi.waybill'
    _description = 'panexlogi.waybill'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = 'billno'

    billno = fields.Char(string='BillNo', readonly=True)

    docno = fields.Char(string='Document No（文件号）', required=False)
    expref = fields.Char(string='Export Refrences', required=False)
    waybillno = fields.Char(string='Waybill No（提单号）', required=False)
    sevtype = fields.Selection(
        [('1', 'FCL/FCL'),
         ('2', 'CY/CY'),
         ('3', 'DR/CY'),
         ('4', 'CY/DR'),
         ('5', 'LCL/LCL'),
         ('6', 'CFS/CFS'), ],
        string='Service Type', default="1")
    # project = fields.Char(string='Project（项目）', required=True)
    project = fields.Many2one('panexlogi.project', string='Project（项目）', required=True, tracking=True)
    date = fields.Date(string='Date（提单日期）', required=True, tracking=True, default=fields.Date.today)
    week = fields.Integer(string='Week-arrival（周数）', compute='_get_week')
    shipping = fields.Many2one('res.partner', string='Shipping Line', domain=[('shipline', '=', 'True')],
                               required=True, tracking=True)
    shipper = fields.Many2one('res.partner', string='Shipper/Exporter',
                              required=True, tracking=True)
    consignee = fields.Many2one('res.partner', string='Consignee/Importer',
                                required=True, tracking=True)
    pdffile = fields.Binary(string='File（原件）')
    pdffilename = fields.Char(string='File name')

    clearance_fee_budget_amount = fields.Float(string="Budget Amount", default=0)
    clearance_fee_settle_amount = fields.Float(string="Settle Amount", default=0)
    clearance_fee_invoice_amount = fields.Float(string="Invoice Amount", default=0)

    handling_fee_budget_amount = fields.Float(string="Budget Amount")
    handling_fee_settle_amount = fields.Float(string="Settle Amount", default=0)
    handling_fee_invoice_amount = fields.Float(string="Invoice Amount", default=0)

    inbound_operating_fee_budget_amount = fields.Float(string="Budget Amount", default=0)
    inbound_operating_fee_settle_amount = fields.Float(string="Settle Amount", default=0)
    inbound_operating_fee_invoice_amount = fields.Float(string="Invoice Amount", default=0)

    inbound_trucking_fee_budget_amount = fields.Float(string="Budget Amount", default=0)
    inbound_trucking_fee_settle_amount = fields.Float(string="Settle Amount", default=0)
    inbound_trucking_fee_invoice_amount = fields.Float(string="Invoice Amount", default=0)

    outbound_operating_fee_budget_amount = fields.Float(string="Budget Amount", default=0)
    outbound_operating_fee_settle_amount = fields.Float(string="Settle Amount", default=0)
    outbound_operating_fee_invoice_amount = fields.Float(string="Invoice Amount", default=0)

    outbound_trucking_fee_budget_amount = fields.Float(string="Budget Amount", default=0)
    outbound_trucking_fee_settle_amount = fields.Float(string="Settle Amount", default=0)
    outbound_trucking_fee_invoice_amount = fields.Float(string="Invoice Amount", default=0)

    entry_num = fields.Float(string="Entry Num")
    extra_num = fields.Float(string="Extra Num")
    pallets_sum = fields.Float(string="Pallets Sum")
    cntr_note = fields.Text(string="Note")

    # 货柜明细
    details_ids = fields.One2many('panexlogi.waybill.details', 'waybill_billno', string='Details')
    # 装箱清单
    packlist_ids = fields.One2many('panexlogi.waybill.packlist', 'waybill_billno', string='Packing List')
    # 到港通知
    arrivnotice_ids = fields.One2many('panexlogi.waybill.arrivnotice', 'waybill_billno', string='Arrival Notice')
    # 商业发票
    commeinvoice_ids = fields.One2many('panexlogi.waybill.commeinvoice', 'waybill_billno', string='Commercial Invoice')
    # 运输发票
    shipinvoice_ids = fields.One2many('panexlogi.waybill.shipinvoice', 'waybill_billno', string='Shipping Invoice')
    # 清关费用发票
    clearinvoice_ids = fields.One2many('panexlogi.waybill.clearinvoice', 'waybill_billno', string='Clearance Invoice')
    # 关税
    customsduties_ids = fields.One2many('panexlogi.waybill.customsduties', 'waybill_billno', string='Customs Duty')
    # 放货证明
    cargorelease_ids = fields.One2many('panexlogi.waybill.cargorelease', 'waybill_billno', string='Cargo Release')
    # 付款申请
    paymentapplication_ids = fields.One2many('panexlogi.finance.paymentapplication', 'waybill_billno',
                                             string='Payment Application')
    color = fields.Integer()
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

    @api.model
    def create(self, values):
        """
        生成跟踪单号
        """
        times = fields.Date.today()
        values['billno'] = self.env['ir.sequence'].next_by_code('seq.waybill', times)
        values['state'] = 'new'
        return super(Waybill, self).create(values)

    # 计算周数
    @api.onchange('week', 'date')
    def _get_week(self):
        for r in self:
            if not r.date:
                r.week = 0
            else:
                r.week = int(r.date.strftime("%W"))

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

    @api.model
    def name_search(self, name, args=None, operator='=', limit=None):
        """
        名称模糊搜索。
        """
        args = args or []
        domain = []
        if 'model' in self.env.context:
            if self.env.context['model'] == 'panexlogi.waybill':
                if self.env.context['project']:
                    # domain.append(('id', 'in', self.env['panexlogi.waybill'].search(
                    #     [('project', '=', self.project)]).ids))
                    domain.append(('project', '=', self.env.context['project']))
        return super(Waybill, self).name_search(name, domain + args, operator=operator, limit=limit)

    # 预算计算
    def action_budget_cal(self):
        entry_num = 0
        extra_num = 0
        pallets_sum = 0
        cntr_note = ""
        clearance_entry_price = 0
        clearance_extra_price = 0
        clearance_fee_budget_amount = 0
        handling_fee_budget_amount = 0
        inbound_operating_fee_budget_amount = 0
        inbound_trucking_fee_budget_amount = 0
        outbound_operating_fee_budget_amount = 0
        if self.details_ids:
            for rec in self.details_ids:
                entry_num = 1
                extra_num += 1
                pallets_sum += rec.pallets
                cntr_note += rec.cntrno + ","
            if extra_num > 0:
                extra_num -= entry_num
            self.entry_num = entry_num
            self.extra_num = extra_num
            self.pallets_sum = pallets_sum
            self.cntr_note = cntr_note

            if self.project.clearance_price_rule:
                clearance_entry_price = self.project.clearance_entry_price
                clearance_extra_price = self.project.clearance_extra_price
                # entry+extra
                clearance_fee_budget_amount = entry_num * clearance_entry_price + extra_num * clearance_extra_price
            self.clearance_fee_budget_amount = clearance_fee_budget_amount

            if self.project.handling_service_charge:
                # per bill
                handling_fee_budget_amount = self.project.handling_service_fee
            self.handling_fee_budget_amount = handling_fee_budget_amount

            if self.project.inbound_operating_fix:
                # per pallets
                inbound_operating_fee_budget_amount = pallets_sum * self.project.inbound_operating_fixfee_per_pallet
            self.inbound_operating_fee_budget_amount = inbound_operating_fee_budget_amount

            if self.project.inbound_trucking_fix:
                # per container
                inbound_trucking_fee_budget_amount = (entry_num + extra_num) * self.project.inbound_trucking_fixfee_per_pallet
            self.inbound_trucking_fee_budget_amount=inbound_trucking_fee_budget_amount

            if self.project.outbound_operating_fix:
                # per pallets
                outbound_operating_fee_budget_amount = pallets_sum * self.project.outbound_operating_fixfee_per_pallet
            self.outbound_operating_fee_budget_amount = outbound_operating_fee_budget_amount

        return True
