from datetime import datetime, timedelta
import requests
import logging
from odoo import _, models, fields, api
from odoo.exceptions import UserError
from collections import defaultdict
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


# 提单
class Waybill(models.Model):
    _name = 'panexlogi.waybill'
    _description = 'panexlogi.waybill'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = 'billno'

    billno = fields.Char(string='BillNo', readonly=True)
    direction = fields.Selection([('import', 'Import'), ('export', 'Export'), ('other', 'Other')], string='Direction',
                                 default='import', required=True, tracking=True)

    docno = fields.Char(string='Document No（文件号）', required=False)
    expref = fields.Char(string='Export Refrences', required=False)
    waybillno = fields.Char(string='Bill of Lading', required=False)
    cntrno = fields.Char(string='EquipmentNumber', required=False)
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

    # List of container numbers and reference numbers
    cntrno_list = fields.Char(string='Container Numbers', compute='_compute_cntrno_list', store=True)

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
    portbase_discharge_terminal = fields.Char(string='Portbase Discharge Terminal')
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
                #r.week = int(r.date.strftime("%W"))
                iso_year, iso_week, iso_day = r.date.isocalendar()
                r.week = iso_week

    def action_confirm_order(self):
        for rec in self:
            if rec.state != 'new':
                raise UserError(_("You only can confirm New Order"))
            else:
                if rec.direction == 'import':
                    if not rec.eta:
                        raise UserError(_("Please select ETA"))
                    if not rec.terminal_a:
                        raise UserError(_("Please select terminal of arrival"))
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
                if rec.shipinvoice_ids.state != 'cancel' and rec.shipinvoice_ids:
                    raise UserError(_("shipping invoice must be cancel first"))
                if rec.clearinvoice_ids.state != 'cancel' and rec.clearinvoice_ids:
                    raise UserError(_("clearance invoice must be cancel first"))
                rec.state = 'cancel'
                return True

    def action_renew_order(self):
        for rec in self:
            if rec.state != 'cancel':
                raise UserError(_("You only can renew Cancelled Order"))
            else:
                rec.state = 'new'
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

    # 生成港倒仓运输单
    def action_transport_order_add(self):
        for record in self:
            # link packlist details
            for rec in record.packlist_ids:
                if rec.cntrno:
                    cntrno = rec.cntrno.strip().upper()
                    domain = [('waybill_billno', '=', record.id), ('cntrno', '=ilike', cntrno)]
                    details = self.env['panexlogi.waybill.details'].search(domain)
                    if details:
                        rec.waybll_detail_id = details.id

            # check if waybill has container details set to inbound
            if not record.details_ids.search([('truck_type', '=', 'inbound'), ('waybill_billno', '=', record.id)]):
                raise UserError(_("Please set container details to inbound first!"))

            if self.env['panexlogi.transport.order'].search(
                    [('waybill_billno', '=', record.id), ('state', '!=', 'cancel')]):
                raise UserError(_("Transport order already exists"))

            if not record.details_ids:
                raise UserError(_("Please add container details first!"))

            if record.details_ids:
                args_list = []
                iRow = 0
                for rec in record.details_ids:
                    if rec.truck_type == 'inbound':
                        """动态合并地址字段，自动跳过空值"""
                        address_parts = []
                        if rec.warehouse.partner_id.street:
                            address_parts.append(rec.warehouse.partner_id.street)
                        if rec.warehouse.partner_id.zip:
                            address_parts.append(rec.warehouse.partner_id.zip)
                        if rec.warehouse.partner_id.city:
                            address_parts.append(rec.warehouse.partner_id.city)
                        if rec.warehouse.partner_id.state_id.name:
                            address_parts.append(rec.warehouse.partner_id.state_id.name)

                        # 用逗号+空格分隔非空字段（例如：Street, 12345 City, State）
                        warehouse_full_address = ', '.join(address_parts) if address_parts else ''
                        args_list.append((0, 0, {
                            'cntrno': rec.cntrno,
                            'pallets': rec.pallets,
                            'uncode': rec.uncode,
                            'coldate': record.eta,
                            'unlodate': record.eta,
                            'warehouse': rec.warehouse.id,
                            'unlolocation': warehouse_full_address,
                            'dropterminal': record.terminal_a.id,
                            'drop_off_planned_date': record.eta,
                            'waybill_detail_id': rec.id,
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
                    'collterminal': record.terminal_a.id,
                    'coldate': record.eta,
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
                # force_send=True,

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

    # 生成配送单
    def action_delivery_request_add(self):
        for rec in self:
            try:
                # 按地址分组集装箱
                address_groups = {}
                # 港口地址（street, zip, city）
                terminal_full_address = ''

                # check if waybill has container details set to delivery
                if not rec.details_ids.search([('truck_type', '=', 'delivery'), ('waybill_billno', '=', rec.id)]):
                    raise UserError(_("Please set container details to delivery first!"))

                # check if delivery request already exists
                domain = [('waybill_detail_id', 'in', rec.details_ids.ids), ('deliveryid.state', '!=', 'cancel')]
                existing_delivery = self.env['panexlogi.delivery.detail'].search(domain)
                if existing_delivery:
                    raise UserError(_("Delivery request already exists"))

                for detail in rec.details_ids.search([('truck_type', '=', 'delivery'), ('waybill_billno', '=', rec.id)]):

                    """动态合并地址字段，自动跳过空值
                    address_parts = []
                    if rec.terminal_a.address.street:
                        address_parts.append(rec.terminal_a.address.street)
                    if rec.terminal_a.address.zip:
                        address_parts.append(rec.terminal_a.address.zip)
                    if rec.terminal_a.address.city:
                        address_parts.append(rec.terminal_a.address.city)

                    # 用逗号+空格分隔非空字段（例如：Street, 12345 City, State）
                    terminal_full_address = ', '.join(address_parts) if address_parts else ''
                    
                    # 生成唯一地址标识
                    address_key = (
                        detail.delivery_address,
                        detail.delivery_company_name,
                        detail.delivery_postcode,
                        detail.delivery_country.id,
                        detail.delivery_contact_phone,
                        detail.delivery_address_timeslot,
                    )
                    """
                    terminal_address = self.env['panexlogi.address'].search([('terminal', '=', rec.terminal_a.id)])

                    address_key = (detail.unload_address)
                    if address_key not in address_groups:
                        address_groups[address_key] = []
                    address_groups[address_key].append(detail)

                # 为每个地址组创建 Delivery 和 Detail
                for addr_key, details_address in address_groups.items():
                    # 为每个集装箱创建 Detail
                    details_vals = []
                    for detail_address in details_address:
                        details_vals.append((0, 0, {
                            'cntrno': detail_address.cntrno,
                            'loading_ref': f"REF-{detail_address.cntrno}",
                            'adr': rec.adr,
                            'uncode': detail_address.uncode,
                            'waybill_detail_id': detail_address.id,
                            'load_address': terminal_address.id,
                            'unload_address': detail_address.unload_address.id,
                        }))
                        # 创建或更新 Delivery 记录
                        delivery_vals = {
                            'delivery_type': detail_address.delivery_type.id,
                            # 'unload_address': addr_key[0],
                            # 'unload_company_name': addr_key[1],
                            # 'unload_postcode': addr_key[2],
                            # 'unload_country': addr_key[3],
                            # 'unload_contact_phone': addr_key[4],
                            # 'unload_address_timeslot': addr_key[5],
                            'project': rec.project.id,
                            # 'load_address': terminal_full_address,
                            # 'load_company_name': rec.shipping.name,
                            # 'load_contact_phone': rec.terminal_a.address.phone,
                            # 'load_postcode': rec.terminal_a.address.zip,
                            # 'load_country': rec.terminal_a.address.country_id.id,
                            'deliverydetatilids': details_vals,
                        }
                        delivery_new = self.env['panexlogi.delivery'].create(delivery_vals)

                        # Send Odoo message
                        subject = 'Transport Order'
                        # Get base URL
                        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                        # Construct URL to transport order
                        delivery_request_url = "{}/web#id={}&model=panexlogi.delivery&view_type=form".format(
                            base_url,
                            delivery_new.id)
                        delivery_request_code = delivery_new.billno
                        # HTML content with button styling
                        content = f'''
                                        <p>Hello,</p>
                                        <p>A new Delivery request has been created:</p>                                
                                        <p>Click the button above to access the details.</p>
                                        '''
                        # Get users in the Delivery group
                        group = self.env['res.groups'].search([('name', '=', 'Delivery')], limit=1)
                        users = self.env['res.users'].search([('groups_id', '=', group.id)])
                        # Get partner IDs from users
                        partner_ids = users.mapped("partner_id").ids
                        # Add Transport group users as followers
                        delivery_new.message_subscribe(partner_ids=partner_ids)
                        # Send message
                        delivery_new.message_post(
                            body=content,
                            subject=subject,
                            message_type='notification',
                            subtype_xmlid="mail.mt_comment",  # Correct subtype for emails
                            body_is_html=True,  # Render HTML in email
                            force_send=True,
                        )

                # return success message
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Success',
                        'message': 'Delivery request create successfully!',
                        'type': 'success',
                        'sticky': False,
                    }
                }
            except Exception as e:
                raise UserError(f"Failed to create delivery request: {e}")

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

    @api.depends('details_ids')
    def _compute_cntrno_list(self):
        for record in self:
            cntrnos = [cntrno for cntrno in record.details_ids.mapped('cntrno') if cntrno]
            record.cntrno_list = ', '.join(cntrnos)

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

    # batch edit
    def open_batch_edit_wizard(self):
        for rec in self:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Batch Edit Container Details',
                'res_model': 'panexlogi.waybill.batch.edit.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_waybill_id': rec.id,
                    'default_detail_ids': rec.details_ids.ids,
                }
            }

    def cron_link_packlist_details(self):
        try:
            """Cron job to link PackList and Details records with matching Waybill + Container No"""
            # Find all PackLists without linked Details
            packlists = self.env['panexlogi.waybill.packlist'].search([
                ('waybll_detail_id', '=', False),
                ('waybill_billno', '!=', False),
                ('cntrno', '!=', False)
            ])
            if packlists:
                # Group PackLists by (waybill_billno, cntrno)
                _logger.info(f"Found {len(packlists)} packlists start to process.")
                grouped_packs = {}
                for pack in packlists:
                    key = (pack.waybill_billno.id, pack.cntrno.strip().upper())  # Normalize cntrno
                    grouped_packs.setdefault(key, []).append(pack)

                # Find existing Details records and link PackLists
                for key, packs in grouped_packs.items():
                    waybill_id, cntrno = key
                    # Search for existing Details with exact match
                    detail = self.env['panexlogi.waybill.details'].search([
                        ('waybill_billno', '=', waybill_id),
                        ('cntrno', '=ilike', cntrno)  # Case-insensitive search
                    ], limit=1)
                    # Skip if no matching Details record is found
                    if not detail:
                        continue
                    # Update all PackLists in the group
                    for pack in packs:
                        pack.write({'waybll_detail_id': detail.id})
                _logger.info(f"Linked {len(packlists)} packlists to details successfully.")
        except Exception as e:
            _logger.error(f"Error in cron_link_packlist_details: {str(e)}")

    def cron_link_transportoder_detail(self):
        try:
            for record in self.search([]):
                # Fetch all waybill details
                details = record.details_ids
                for rec in details:
                    cntrno = ''
                    if rec.cntrno:
                        cntrno = rec.cntrno.strip().upper()
                    # Search for transport order details with matching waybill and container number
                    if cntrno != '':
                        transport_order_detail = self.env['panexlogi.transport.order.detail'].search([
                            ('transportorderid.waybill_billno', '=', record.id),
                            ('cntrno', '=ilike', cntrno),
                            ('waybill_detail_id', '=', False)  # Ensure it's not already linked
                        ], limit=1)

                        # Skip if no matching transport order detail is found
                        if not transport_order_detail:
                            continue
                        else:
                            transport_order_detail.write({'waybill_detail_id': rec.id})

        except Exception as e:
            _logger.error(f"Error in cron_link_transportoder_detail: {str(e)}")

    def fetch_portbase_data(self):
        self.ensure_one()
        try:
            # API configuration
            portbase_access_key_id = self.env['ir.config_parameter'].sudo().get_param('portbase-access-key-id')
            portbase_secret_access_key = self.env['ir.config_parameter'].sudo().get_param('portbase-secret-access-key')
            portbase_tracked_bls = self.env['ir.config_parameter'].sudo().get_param('portbase-tracked-bls')
            portbase_track_requests = self.env['ir.config_parameter'].sudo().get_param('portbase-track-requests')

            headers = {
                'portbase-access-key-id': portbase_access_key_id,
                'portbase-secret-access-key': portbase_secret_access_key,
                'Content-Type': 'application/json'
            }
            # Step 1: Create track request

            payload = {
                "trackRequests": [{
                    "transportEquipmentNumber": self.cntrno,
                    "blNumber": self.waybillno
                }]
            }
            try:
                response = requests.post(portbase_track_requests, headers=headers, json=payload)
                response.raise_for_status()
                track_data = response.json()
            except Exception as e:
                raise UserError(_('API Error: %s') % str(e))

            # Get tracking ID
            tracked_bls = track_data.get('trackedBLs', [])
            if not tracked_bls:
                raise UserError(_('No tracked BLS found in the response.'))
            tracking_id = tracked_bls[0]['id']

            # Step 2: Get detailed tracking data
            detail_url = f'{portbase_tracked_bls}?id={tracking_id}'
            try:
                response = requests.get(detail_url, headers=headers)
                response.raise_for_status()
                bl_data = response.json()
            except Exception as e:
                raise UserError(_('API Error: %s') % str(e))

            if not bl_data:
                raise UserError(_(f'No data found for the given tracking ID: {tracking_id}.'))
            bill_of_lading = bl_data[0].get('billOfLading', {})
            vessel_visit = bill_of_lading.get('vesselVisit', {})
            visit_declaration = vessel_visit.get('visitDeclaration', {})
            port_visit = visit_declaration.get('portVisit', {})

            # Update ETA and terminal information
            update_vals = {}

            # Parse ETA date
            if port_visit.get('etaPort'):
                try:
                    eta_date_str = port_visit['etaPort'].split('T')[0]  # Get date part only
                    ata_date_str = port_visit['ataPort'].split('T')[0]  # Get date part only
                    update_vals['eta'] = datetime.strptime(eta_date_str, '%Y-%m-%d').date()
                    update_vals['ata'] = datetime.strptime(ata_date_str, '%Y-%m-%d').date()
                except Exception as e:
                    _logger.error("Error parsing ETA date: %s", str(e))

            # Handle terminal information
            discharge_terminal = bill_of_lading.get('dischargeTerminal', {})
            if discharge_terminal:
                update_vals['portbase_discharge_terminal'] = discharge_terminal.get('ownerFullName', '')

            # Write the update values to the waybill
            if update_vals:
                self.write(update_vals)

            # Filter only the container we requested
            transport_equipments = [
                eq for eq in bill_of_lading.get('transportEquipments', [])
                if eq.get('equipmentNumber') == self.cntrno
            ]
            goods_items = bill_of_lading.get('goodsItems', [])
            # Group goods items by container
            equipment_goods = defaultdict(list)
            for gi in goods_items:
                for ge in gi.get('goodsItemTransportEquipments', []):
                    if ge.get('equipmentNumber') == self.cntrno:
                        equipment_goods[self.cntrno].append(gi)

            # Process container details
            for equipment in transport_equipments:
                # Create/update detail line
                detail = self.details_ids.filtered(
                    lambda d: d.cntrno == equipment['equipmentNumber']
                )
                detail_vals = {
                    'cntrno': equipment['equipmentNumber'],
                    'cntrnum': 1,
                    'pallets': sum(
                        gi['numberOfOuterPackages']
                        for gi in goods_items
                        if any(ge['equipmentNumber'] == equipment['equipmentNumber']
                               for ge in gi['goodsItemTransportEquipments'])
                    ),
                    'note': equipment.get('oversizeRemarks', ''),
                    'waybill_billno': self.id,
                }
                # Check if detail already exists
                if not detail:
                    new_detail = self.details_ids.create(detail_vals)
                    id_int_new = new_detail.id
                    # Get goods items SPECIFIC to this container
                    container_goods = [
                        gi for gi in goods_items
                        if any(ge['equipmentNumber'] == equipment['equipmentNumber']
                               for ge in gi['goodsItemTransportEquipments'])
                    ]

                    # Process packing list items
                    packlist_lines = []
                    for gi in container_goods:
                        commodity_data = gi.get('commodity', {})

                        packlist_vals = {
                            'portbase_product_code': commodity_data.get('code', ''),
                            'portbase_product': commodity_data.get('description', ''),
                            'pcs': gi.get('numberOfOuterPackages', 0),
                            'pallets': gi.get('numberOfOuterPackages', 0),
                            'gw': gi.get('grossWeight', 0),
                            'cntrno': equipment['equipmentNumber'],
                            'sealno': equipment.get('carrierSealNumber', ''),
                            'waybill_billno': self.id,
                            'waybll_detail_id': id_int_new,
                        }
                        packlist_lines.append((0, 0, packlist_vals))
                    new_detail.write({'waybill_packlist_id': packlist_lines})

                # Update records
                """
                if detail:
                    # detail.write(detail_vals)
                    # detail.waybill_packlist_id = [(5, 0, 0)] + packlist_lines
                    pass
                else:
                    detail_vals['waybill_billno'] = self.id
                    detail_vals['waybill_packlist_id'] = packlist_lines
                    new_detail = self.env['panexlogi.waybill.details'].create(detail_vals)
                    #new_detail.waybill_packlist_id = packlist_lines
                """
                # return success message
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Success',
                    'message': 'Portbase data fetched successfully!',
                    'type': 'success',
                    'sticky': False,
                    'next': {
                        'type': 'ir.actions.client',
                        'tag': 'reload',
                    }
                }
            }
        except Exception as e:
            raise UserError(f"Failed to fetch Portbase data: {e}")

    @api.depends('packlist_ids')
    def _autolink_detail_auto_link(self):
        for record in self:
            record.cron_link_packlist_details()

# 其他附件
class WaybillOtherDocs(models.Model):
    _name = 'panexlogi.waybill.otherdocs'
    _description = 'panexlogi.waybill.otherdocs'

    description = fields.Text(string='Description')
    file = fields.Binary(string='File')
    filename = fields.Char(string='File name')
    waybill_billno = fields.Many2one('panexlogi.waybill', string='Waybill BillNo')
