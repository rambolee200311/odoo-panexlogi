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

    # 货柜明细
    details_ids=fields.One2many('panexlogi.waybill.details', 'waybill_billno', string='Details')
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
