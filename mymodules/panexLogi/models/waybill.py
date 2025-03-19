from datetime import datetime, timedelta
import pytz
import logging
from odoo import _, models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


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
    project_type = fields.Many2one('panexlogi.project.type', string='Project Type')
    date = fields.Date(string='Date（提单日期）', required=True, tracking=True, default=fields.Date.today)
    week = fields.Integer(string='Week-arrival（周数）', compute='_get_week')
    shipping = fields.Many2one('res.partner', string='Shipping Line', domain=[('shipline', '=', 'True')],
                               tracking=True)
    shipper = fields.Many2one('res.partner', string='Shipper/Exporter',
                              tracking=True)
    consignee = fields.Many2one('res.partner', string='Consignee/Importer',
                                tracking=True)
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

    # 其他附件
    otherdocs_ids = fields.One2many('panexlogi.waybill.otherdocs', 'waybill_billno', string='Other Docs')
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
    first_arrivnotice_date = fields.Date(string='First Arrival Notice Date', compute='_compute_first_arrivnotice_date')
    adr = fields.Boolean(string='ADR')
    remark = fields.Text(string='Remark')
    '''
    ETD: 预计离港日期
    ATD: 实际离港日期
    ATA: 实际到港日期
    ETA: 预计到港日期
    '''

    etd = fields.Date(string='ETD', tracking=True)
    atd = fields.Date(string='ATD', tracking=True)
    terminal_d = fields.Char(string='Terminal of Departure', tracking=True)
    eta = fields.Date(string='ETA', tracking=True)
    ata = fields.Date(string='ATA', tracking=True, readonly=True)
    terminal_a = fields.Many2one('panexlogi.terminal', string='Terminal of Arrival', tracking=True)
    eta_remark = fields.Text(string='ETA Remark')
    transport_order = fields.One2many('panexlogi.transport.order', 'waybill_billno', string='Transport Order')

    # Autofill project_type when project is selected
    @api.onchange('project')
    def _onchange_project(self):
        for record in self:
            if record.project:
                record.project_type = record.project.project_type
            else:
                record.project_type = False

    @api.depends('arrivnotice_ids.date')
    def _compute_first_arrivnotice_date(self):
        for record in self:
            if record.arrivnotice_ids:
                record.first_arrivnotice_date = record.arrivnotice_ids[0].date
            else:
                record.first_arrivnotice_date = False

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
                if rec.shipinvoice_ids.state != 'cancel':
                    raise UserError(_("shipping invoice must be cancel first"))
                if rec.clearinvoice_ids.state != 'cancel':
                    raise UserError(_("clearance invoice must be cancel first"))
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
                inbound_trucking_fee_budget_amount = (
                                                             entry_num + extra_num) * self.project.inbound_trucking_fixfee_per_pallet
            self.inbound_trucking_fee_budget_amount = inbound_trucking_fee_budget_amount

            if self.project.outbound_operating_fix:
                # per pallets
                outbound_operating_fee_budget_amount = pallets_sum * self.project.outbound_operating_fixfee_per_pallet
            self.outbound_operating_fee_budget_amount = outbound_operating_fee_budget_amount

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': 'Budget calculate successfully!',
                'type': 'success',
                'sticky': False,
            }
        }

    # 生成运输单
    def action_tranportorder_add(self):

        for record in self:
            if self.env['panexlogi.transport.order'].search(
                    [('waybill_billno', '=', record.id), ('state', '!=', 'cancel')]):
                raise UserError(_("Transport order already exists"))

            if not record.details_ids:
                raise UserError(_("Please add container details first!"))

            if record.details_ids:
                args_list = []
                iRow = 0
                for rec in record.details_ids:
                    args_list.append((0, 0, {
                        'cntrno': rec.cntrno,
                        'pallets': rec.pallets,
                        'uncode': rec.uncode,
                    }))
                    iRow += 1

                if iRow == 0:
                    raise UserError(_("Please add container details first!"))
                # 更新当前记录的关联字段
                transport_order_vals = {
                    'waybill_billno': record.id,
                    'project': record.project.id,
                    'date': fields.Date.today(),
                    'state': 'new',
                    'transportorderdetailids': args_list,
                    'adr': record.adr,

                }
                try:
                    # 创建运输单
                    transport_order = self.env['panexlogi.transport.order'].create(transport_order_vals)
                except Exception as e:
                    raise UserError(f"Failed to create transport order: {e}")




                # Send Odoo message
                subject = 'Transport Order'
                # Get base URL
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                # Construct URL to transport order
                transport_order_url = "{}/web#id={}&model=panexlogi.transport.order&view_type=form".format(base_url,
                                                                                                           transport_order.id)
                transport_order_code = transport_order.billno
                # content = 'Transport order: <a href="{}">{}</a> created successfully!'.format(transport_order_url,
                #                                                                              transport_order.billno)

                # HTML content with button styling
                content = f'''
                <p>Hello,</p>
                <p>A new transport order has been created:</p>                                
                <p>Click the button above to access the details.</p>
                '''

                # Get users in the Transport group
                group = self.env['res.groups'].search([('name', '=', 'Transport')], limit=1)
                users = self.env['res.users'].search([('groups_id', '=', group.id)])
                # Get partner IDs from users
                partner_ids = users.mapped("partner_id").ids
                # Add Transport group users as followers
                transport_order.message_subscribe(partner_ids=partner_ids)
                # Send message
                transport_order.message_post(
                    body=content,
                    subject=subject,
                    message_type='notification',
                    subtype_xmlid="mail.mt_comment",  # Correct subtype for emails
                    body_is_html=True,  # Render HTML in email
                    force_send=True,
                )
                #force_send=True,

                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Success',
                        'message': 'Transport order create successfully!',
                        'type': 'success',
                        'sticky': False,
                    }
                }

            else:
                raise UserError(_("Please add container details first!"))

    # 维护到港实际日期 跳转wizard视图
    def add_actual_date(self):
        return {
            'name': 'Actual Arrival Date',
            'type': 'ir.actions.act_window',
            'res_model': 'panexlogi.waybill.arrivnotice.wizard',
            'view_mode': 'form',
            'target': 'new',
        }

    # check waybillno unique
    @api.constrains('waybillno')
    def _check_waybillno_id(self):
        for r in self:
            domain = [
                ('waybillno', '=', r.waybillno),
                ('state', '!=', 'cancel'),
                ('id', '!=', r.id),
            ]
            existing_records = self.search(domain)
            if existing_records:
                raise UserError(_('waybillno must be unique per Waybill'))

    def unlink(self):
        for rec in self:
            if rec.state != 'cancel':
                raise UserError(_("You can not delete approved or rejected quote, try to cancel it first"))
            rec.details_ids.unlink()
            rec.packlist_ids.unlink()
            rec.arrivnotice_ids.unlink()
            rec.commeinvoice_ids.unlink()
            if rec.shipinvoice_ids.state == 'cancel':
                rec.shipinvoice_ids.unlink()
            else:
                raise UserError(_("shipping invoice must be cancel first"))
            if rec.clearinvoice_ids.state == 'cancel':
                rec.clearinvoice_ids.unlink()
            else:
                raise UserError(_("clearance invoice must be cancel first"))
            rec.customsduties_ids.unlink()
            rec.cargorelease_ids.unlink()
            rec.otherdocs_ids.unlink()
        return super(Waybill, self).unlink()

    @api.model
    def cron_check_eta_reminder(self):
        """Check for eta."""
        # Set a deadline of 7 days ago
        deadline = fields.Date.today() - timedelta(days=7)
        domain = [('eta', '<=', deadline),
                  ('state', '!=', 'cancel'),
                  ('cargorelease_ids', '=', False)]
        waybills = self.search(domain)
        try:
            for record in waybills:
                if record.eta and record.eta <= deadline:
                    # Get the project group
                    # project_group = record.project.group
                    # users = self.env['res.users'].search([('groups_id', '=', project_group.id)])
                    # users = self.env['res.users'].search([('name', '=', '163com-Demo')])
                    # partner_ids = users.mapped("partner_id").ids
                    # partner_ids=self.env['res.users'].search([('groups_id', '=', record.project.group.id)]).mapped("partner_id").ids,
                    record.message_subscribe(
                        partner_ids=self.env['res.users'].search([('groups_id', '=', record.project.group.id)]).mapped(
                            "partner_id").ids)
                    subject = 'ETA Reminder'
                    content = (
                        f"⚠️ <strong>ETA Reminder</strong><br/>"
                        f"Please prepare the documents for releasing.<br/>"
                        f"The ETA is {record.eta}'.<br/>"
                        f"<i>This is an automated reminder.</i>")
                    record.message_post(
                        body=content,
                        subject=subject,
                        message_type='notification',
                        subtype_xmlid="mail.mt_comment",  # Correct subtype for emails
                        body_is_html=True,  # Render HTML in email
                        force_send=True,
                    )
        except Exception as e:
            _logger.error(f"Error in ETA reminder: {str(e)}")
        return  # Explicitly return None
    # UI button for the current record
    def button_check_eta_reminder(self):
        """Called via the UI button for the current record."""
        self.ensure_one()  # Ensure only one record is processed
        self.cron_check_eta_reminder()  # Reuse the cron logic


# 其他附件
class WaybillOtherDocs(models.Model):
    _name = 'panexlogi.waybill.otherdocs'
    _description = 'panexlogi.waybill.otherdocs'

    description = fields.Text(string='Description')
    file = fields.Binary(string='File')
    filename = fields.Char(string='File name')
    waybill_billno = fields.Many2one('panexlogi.waybill', string='Waybill BillNo')
