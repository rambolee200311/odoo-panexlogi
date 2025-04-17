from datetime import datetime, timedelta
import pytz
from openpyxl.styles import Font
from openpyxl.styles import Alignment

from odoo import _, models, fields, api, exceptions
from odoo.exceptions import UserError, ValidationError
import logging
import base64
from io import BytesIO
import openpyxl

_logger = logging.getLogger(__name__)


# 卡车运单
class Delivery(models.Model):
    _name = 'panexlogi.delivery'
    _description = 'panexlogi.delivery'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = 'billno'

    billno = fields.Char(string='BillNo', readonly=True)
    date = fields.Date(string='Date', default=fields.Date.today())
    project = fields.Many2one('panexlogi.project', string='Project（项目）')

    inner_ref = fields.Char(string='Inner Ref')
    loading_ref = fields.Char(string='Loading Ref')
    consignee_ref = fields.Char(string='Consignee Ref')

    remark = fields.Text(string='Remark')

    # load type
    load_type = fields.Selection(
        selection=[
            ('warehouse', 'Warehouse'),
            ('terminal', 'Terminal'),
            ('other', 'Other'),
        ],
        string='Load Type',
        default='other'
    )
    load_warehouse = fields.Many2one('stock.warehouse', string='Warehouse')
    load_terminal = fields.Many2one('panexlogi.terminal', string='Terminal')

    load_address = fields.Char(string='Address')
    load_company_name = fields.Char(string='Company Name')
    load_contact_phone = fields.Char(string='Contact Phone')
    load_postcode = fields.Char(string='Postcode')
    # city
    load_city = fields.Char(string='City')
    load_country = fields.Many2one('res.country', 'Load Coutry')
    load_country_code = fields.Char('Country Code', related='load_country.code')
    load_address_timeslot = fields.Char('Timeslot')
    unload_address = fields.Char(string='Address')
    unload_company_name = fields.Char(string='Company Name')
    unload_contact_phone = fields.Char(string='Contact Phone')
    unload_postcode = fields.Char(string='Postcode')
    # city
    unload_city = fields.Char(string='City')
    unload_country = fields.Many2one('res.country', 'Unload Country')
    unload_country_code = fields.Char('Country Codde', related='unload_country.code')
    unload_address_timeslot = fields.Char('Timeslot')
    delivery_type = fields.Many2one('panexlogi.deliverytype', 'Delivery Type')
    loading_conditon = fields.Many2one('panexlogi.loadingcondition', ' Condition')
    unloading_conditon = fields.Many2one('panexlogi.loadingcondition', 'Condition')
    planned_for_loading = fields.Datetime(string='Planned Loading')
    planned_for_unloading = fields.Datetime(string='Planned Unloading')
    quote = fields.Float('Quote', default=0, tracking=True, readonly=True)
    charged = fields.Float('Charged', default=0, tracking=True)
    profit = fields.Float('Profit', default=0)
    trucker = fields.Many2one('res.partner', string='Trucker', domain=[('truck', '=', 'True')])
    loading_date = fields.Datetime(string='Loading Date')
    # delivery_date = fields.Datetime(string='Delivery Date')
    unloading_date = fields.Datetime(string='Unloading Date')
    additional_cost = fields.Float('Additional Cost', default=0, tracking=True, readonly=True)  # 额外费用
    extra_cost = fields.Float('Extra Cost', default=0, tracking=True, readonly=True)
    notes = fields.Text('Notes')
    deliverydetatilids = fields.One2many('panexlogi.delivery.detail', 'deliveryid', 'Delivery Detail')
    deliveryquoteids = fields.One2many('panexlogi.delivery.quote', 'delivery_id', 'Delivery Quote')
    deliverystatusids = fields.One2many('panexlogi.delivery.status', 'delivery_id', 'Delivery Status')
    deliveryotherdocsids = fields.One2many('panexlogi.delivery.otherdocs', 'billno', 'Other Docs')

    pdffile = fields.Binary(string='POD File')
    pdffilename = fields.Char(string='POD File name')

    need_inform = fields.Boolean(string='Need', default=False)
    inform_date = fields.Date(string='Date')
    inform_content = fields.Text(string='Content')
    inform_receiver = fields.Many2many('res.partner', string='Receivers',
                                       domain=[('user_ids', '!=', False), ('email', '!=', False)])
    inform_email_to = fields.Char(compute='_compute_email_to', string="Email To", store=True)
    delivery_order_id = fields.Many2one('panexlogi.delivery.order', string='Delivery Order')
    color = fields.Integer()
    state = fields.Selection(
        selection=[
            ('new', 'New'),
            ('confirm', 'Confirm'),
            ('order', 'Order'),
            ('cancel', 'Cancel'),
        ],
        default='new',
        string="State",
        tracking=True
    )
    adr = fields.Boolean(string='ADR')
    # List of container numbers and reference numbers
    cntrno_list = fields.Char(string='Container Numbers', compute='_compute_cntrno_list', store=True)
    ref_list = fields.Char(string='Reference Numbers', compute='_compute_cntrno_list', store=True)

    delivery_detail_cmr_ids = fields.One2many('panexlogi.delivery.detail.cmr', 'delivery_id', string='CMR IDs')

    @api.onchange('load_warehouse')
    def _onchange_load_warehouse(self):
        if self.load_warehouse and self.load_type == 'warehouse':
            self.load_terminal = False
            self.load_address = self.load_warehouse.partner_id.street
            self.load_company_name = self.load_warehouse.partner_id.name
            self.load_postcode = self.load_warehouse.partner_id.zip
            self.load_city = self.load_warehouse.partner_id.city
            self.load_country = self.load_warehouse.partner_id.country_id.id

    @api.onchange('load_terminal')
    def _onchange_load_terminal(self):
        if self.load_terminal and self.load_type == 'terminal':
            self.load_warehouse = False
            self.load_address = self.load_terminal.address.street
            self.load_company_name = self.load_terminal.address.name
            self.load_postcode = self.load_terminal.address.zip
            self.load_city = self.load_terminal.address.city
            self.load_country = self.load_terminal.address.country_id.id

    @api.constrains('load_type', 'load_warehouse', 'load_terminal')
    def _check_load_type(self):
        for record in self:
            if record.load_type == 'warehouse' and not record.load_warehouse:
                raise ValidationError(_("Please select a warehouse."))
            if record.load_type == 'terminal' and not record.load_terminal:
                raise ValidationError(_("Please select a terminal."))

    @api.depends('deliverydetatilids')
    def _compute_cntrno_list(self):
        for record in self:
            cntrnos = [cntrno for cntrno in record.deliverydetatilids.mapped('cntrno') if cntrno]
            refs = [ref for ref in record.deliverydetatilids.mapped('loading_ref') if ref]
            record.cntrno_list = ', '.join(cntrnos)
            record.ref_list = ', '.join(refs)

    def action_confirm_order(self):
        for rec in self:
            if rec.state != 'new':
                raise UserError(_("You only can confirm New Order"))
            else:
                # Check if the delivery details are empty
                if not rec.deliverydetatilids:
                    raise UserError(_("You must add delivery details before confirming."))
                else:
                    # Check if the delivery details loading_ref or cntrno is empty
                    for detail in rec.deliverydetatilids:
                        if not detail.loading_ref and not detail.cntrno:
                            raise ValidationError(_("Either Loading Ref or Container No is required."))

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

    @api.onchange('quote', 'charged', 'extra_cost', 'additional_cost')
    def _onchange_profit(self):
        for r in self:
            r.profit = r.charged - r.quote - r.extra_cost - r.additional_cost

    @api.model
    def create(self, values):
        """
        生成跟踪单号
        """
        times = fields.Date.today()
        values['billno'] = self.env['ir.sequence'].next_by_code('seq.delivery', times)
        delivery_request = super(Delivery, self).create(values)
        # Add followers after creation
        # Get Transport group users via XML ID (replace with your actual XML ID)
        transport_group = self.env['res.groups'].search([('name', '=', 'Transport')], limit=1)
        users = self.env['res.users'].search([('groups_id', '=', transport_group.id)])
        partner_ids = users.mapped('partner_id').ids
        # Subscribe followers to the record
        if partner_ids:
            delivery_request.message_subscribe(partner_ids=partner_ids)
        return delivery_request

    def write(self, vals):
        # Notify the creator when tracked fields change
        quote_tracked_fields = {'deliveryquoteids', 'billno'}
        if quote_tracked_fields.intersection(vals.keys()):
            self._send_inform_quote_content()
        status_tracked_fields = {'deliverystatusids', 'delivery_id'}
        if status_tracked_fields.intersection(vals.keys()):
            self._send_inform_status_content()
        return super(Delivery, self).write(vals)

    # 跳转wizard视图
    def add_delivery_status(self):
        return {
            'name': 'Add Status',
            'type': 'ir.actions.act_window',
            'res_model': 'panexlogi.delivery.status.wizard',
            'view_mode': 'form',
            'target': 'new',
        }

    # recalculate extra cost
    def _get_extra_cost(self):
        extra_cost = 0
        for r in self.deliverystatusids:
            extra_cost += r.extra_cost
        self.extra_cost = extra_cost

    # automatically send Odoo messages when quote is created
    def _send_inform_quote_content(self):
        for record in self:
            subject = 'Delivery Quote Submitted'
            content = f'Delivery Quote has been submitted for {record.billno}.'
            # Get the creator's partner ID
            creator_partner = record.create_uid.partner_id
            record.message_post(
                body=content,
                subject=subject,
                partner_ids=[creator_partner.id],  # Notify only the creato
                message_type='notification',
                subtype_xmlid="mail.mt_comment",  # Correct subtype for emails
                body_is_html=True,  # Render HTML in email
                force_send=True,
            )
            # force_send=True,

    # automatically send Odoo messages when status is created
    def _send_inform_status_content(self):
        for record in self:
            subject = 'Delivery Status Updated'
            content = f'Delivery Status has been updated for {record.billno}.'
            # Get the creator's partner ID
            creator_partner = record.create_uid.partner_id
            record.message_post(
                body=content,
                subject=subject,
                partner_ids=[creator_partner.id],  # Notify only the creato
                message_type='notification',
                subtype_xmlid="mail.mt_comment",  # Correct subtype for emails
                body_is_html=True,  # Render HTML in email
                force_send=True,
            )
            # force_send=True,

    # automatically send emails and Odoo messages
    def _send_inform_content(self):
        automatically = True
        self._send_delivery_emails(automatically)

    # get email recipients
    @api.depends('inform_receiver')
    def _compute_email_to(self):
        for record in self:
            # Filter partners with valid emails
            valid_partners = record.inform_receiver.filtered(lambda p: p.email)
            emails = valid_partners.mapped('email')
            record.inform_email_to = ', '.join(emails) if emails else False  # Set to False if empty
            _logger.debug('Computed inform_email_to: %s', record.inform_email_to)

    # manually send emails and Odoo messages
    def send_delivery_emails(self):
        automatically = False
        self._send_delivery_emails(automatically)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': 'Delivery Inform Successfully!',
                'type': 'success',
                'sticky': False,
            }
        }

    def _send_delivery_emails(self, automatically=False):
        now = fields.Date.today()  # UTC-aware
        tomorrow = now + timedelta(days=1)
        subject = 'Delivery Inform'
        # Filter deliveries
        if automatically:
            deliveries = self.search([
                ('inform_date', '<=', tomorrow),  # Use <= for safety
                ('need_inform', '=', True)
            ])
            subject += f'(auto-{now})'
        else:
            deliveries = self
            subject += f'(manu-{now})'

        server_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        current_user_email = self.env.user.email
        for delivery in deliveries:
            if delivery.inform_receiver:
                # template_id = self.env.ref('panexLogi.email_delivery_template_inform_content').id
                # self.env['mail.template'].browse(template_id).send_mail(delivery.id, force_send=True)
                bill_url = f'{server_url}/web#id={delivery.id}&model=panexlogi.delivery&view_type=form'
                logo_url = f'{server_url}/logo.png?company={self.env.user.company_id.id}'
                content = f'Content:{delivery.inform_content}'
                # Send email
                """
                mail_values = {
                    'subject': subject,
                    'email_to': delivery.inform_email_to or 'fallback@example.com',  # Ensure email is set
                    'body_html': f'''
                                         <div>
                                            <p>Please focus on </p>
                                            <p>Bill No: <a href="{bill_url}">{delivery.billno}</a></p>
                                            <p>{content}</p>
                                         </div>   
                                         <div>
                                            <p>Best regards,</p>
                                            <p>{self.env.user.name}</p>
                                            <img src="{logo_url}" alt="Company Logo" />
                                         </div>
                                        ''',
                    'email_from': current_user_email
                }
                self.env['mail.mail'].create(mail_values).send()
                message_type='comment',
                """
                # Send Odoo message
                delivery.message_post(
                    body=content,
                    subject=subject,
                    partner_ids=delivery.inform_receiver.ids,
                    message_type='notification',
                    subtype_xmlid='mail.mt_note',
                    email_layout_xmlid='mail.mail_notification_light',  # Force email layout
                    force_send=True,  # Send immediately, bypassing the queue
                )

    # 2025018 wangpeng pod reminder
    @api.model
    def _cron_check_pod_reminder(self):
        """Check for overdue deliveries and send reminders."""
        try:
            deadline = fields.Datetime.now() - timedelta(days=14)
            overdue_deliveries = self.search([
                ('planned_for_unloading', '<=', deadline),
                ('pdffile', '=', False),
            ])
            # template = self.env['mail.template'].search([('name', '=', 'Panex POD Reminder')], limit=1)
            if overdue_deliveries:
                # ✅ Fix: Do NOT return the list from send_mail()
                # template.send_mail(overdue_deliveries.ids, force_send=True)
                # _logger.info(f"Sent reminders for {len(overdue_deliveries)} deliveries.")
                # Get users in the Finance group
                group = self.env['res.groups'].search([('name', '=', 'Delivery')], limit=1)
                users = self.env['res.users'].search([('groups_id', '=', group.id)])
                # Get partner IDs from users
                partner_ids = users.mapped("partner_id").ids
                # Send reminders one by one
                for delivery in overdue_deliveries:
                    message = (
                        f"⚠️ <strong>POD Missing Reminder</strong><br/>"
                        f"Delivery {delivery.billno} has no POD uploaded. "
                        f"Planned unloading date was {delivery.planned_for_unloading}.<br/>"
                        f"<i>This is an automated reminder.</i>"
                    )
                    delivery.message_post(
                        subject="POD Missing Reminder",
                        body=message,
                        partner_ids=partner_ids,
                        message_type='notification',
                        subtype_xmlid="mail.mt_comment",  # Correct subtype for emails
                        body_is_html=True,  # Render HTML in email
                        force_send=True,
                    )
                    # force_send=True,
        except Exception as e:
            _logger.error(f"Error in POD reminder: {str(e)}")
        return  # Explicitly return None

    # create delivery order
    def action_create_delivery_order(self):
        return {
            'name': _('Create Delivery Orders'),
            'type': 'ir.actions.act_window',
            'res_model': 'panexlogi.delivery.detail.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_delivery_id': self.id,
                'form_view_ref': 'panexLogi.view_delivery_detail_wizard_form'
            }
        }

    # create delivery cmr
    def action_create_delivery_cmr(self):
        return {
            'name': _('Create Delivery Cmr'),
            'type': 'ir.actions.act_window',
            'res_model': 'panexlogi.delivery.detail.cmr.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_delivery_id': self.id,
                'form_view_ref': 'panexLogi.view_delivery_detail_cmr_wizard_form'
            }
        }

    @api.model
    def _create_single_delivery_order(self, recs):
        try:
            # request.detail
            dts = []
            for rec in recs:
                dts.append({
                    'cntrno': rec.cntrno,
                    'product': rec.product.id,
                    'pallets': rec.pallets,
                    'qty': rec.qty,
                    'batch_no': rec.batch_no,
                    'model_type': rec.model_type,
                    'package_type': rec.package_type.id,
                    'package_size': rec.package_size,
                    'weight_per_unit': rec.weight_per_unit,
                    'gross_weight': rec.gross_weight,
                    'uncode': rec.uncode,
                    'class_no': rec.class_no,
                    'adr': rec.adr,
                    'remark': rec.remark,
                    'quote': rec.quote,
                    'additional_cost': rec.additional_cost,
                    #'delivery_id': rec.deliveryid.id,
                    'delivery_detail_id': rec.id,
                })
            delivery_order_vals = {
                'delivery_detail_id': recs[0].id,
                'delivery_id': recs[0].deliveryid.id,
                'project': recs[0].deliveryid.project.id,
                'truckco': recs[0].deliveryid.trucker.id,
                'delivery_type': recs[0].deliveryid.delivery_type.id,
                'loading_ref': recs[0].loading_ref,
                'unloading_ref': recs[0].consignee_ref,
                'loading_condition': recs[0].load_condition.id,
                'unloading_condition': recs[0].unload_condition.id,
                #'planned_for_loading': recs[0].deliveryid.planned_for_loading,
                #'planned_for_unloading': recs[0].deliveryid.planned_for_unloading,
                #'load_type': recs[0].deliveryid.load_type,
                #'load_warehouse': recs[0].load_warehouse.id,
                #'load_terminal': recs[0].load_terminal.id,
                'loading_address': recs[0].load_address.id,
                #'load_company_name': recs[0].deliveryid.load_company_name,
                #'load_contact_phone': recs[0].deliveryid.load_contact_phone,
                #'load_postcode': recs[0].deliveryid.load_postcode,
                #'load_city': recs[0].deliveryid.load_city,
                #'load_country': recs[0].deliveryid.load_country.id,
                #'load_country_code': recs[0].deliveryid.load_country_code,
                'load_address_timeslot': recs[0].load_timeslot,
                'unloading_address': recs[0].unload_address.id,
                #'unload_company_name': recs[0].deliveryid.unload_company_name,
                #'unload_contact_phone': recs[0].deliveryid.unload_contact_phone,
                #'unload_postcode': recs[0].deliveryid.unload_postcode,
                #'unload_city': recs[0].deliveryid.unload_city,
                #'unload_country': recs[0].deliveryid.unload_country.id,
                #'unload_country_code': recs[0].deliveryid.unload_country_code,
                'unload_address_timeslot': recs[0].unload_timeslot,
                'delivery_order_line_ids': [(0, 0, dt) for dt in dts],
            }
            delivery_order = self.env['panexlogi.delivery.order'].create(delivery_order_vals)

            #for rec in recs:
            #    rec.write({
                    #'state': 'order',
                    #'delivery_order_id': delivery_order.id
            #    })

        except Exception as e:
            raise UserError(_("Error creating delivery order: %s") % str(e))

    # batch edit
    def open_batch_edit_wizard(self):
        for rec in self:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Batch Edit Details',
                'res_model': 'panexlogi.delivery.detail.batch.edit.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_delivery_id': rec.id,
                    'default_detail_ids': rec.deliverydetatilids.ids,
                }
            }

    #@api.model
    def cron_create_addresses(self):
        """Cron job to create addresses for deliveries."""
        try:
            deliveries = self.search([])  # Fetch all deliveries
            for delivery in deliveries:
                # Create load address if load_address and load_company_name exist
                if delivery.load_address:
                    domain = [('street', '=', delivery.load_address)]
                    existing_address = self.env['panexlogi.address'].search(domain)
                    if not existing_address:
                        load_address = self.env['panexlogi.address'].create({
                            'is_warehouse': False,
                            'warehouse': False,
                            'is_terminal': False,
                            'terminal': False,
                            'street': delivery.load_address,
                            'company_name': delivery.load_company_name,
                            'country': delivery.load_country.id,
                            'city': delivery.load_city,
                            'postcode': delivery.load_postcode,
                        })
                        _logger.info(f"Created load address: {load_address.street}")
                        for rec in delivery.deliverydetatilids:
                            if not rec.load_address:
                                rec.write({
                                    'load_address': load_address.id,
                                })

                # Create unload address if unload_address and unload_company_name exist
                if delivery.unload_address:
                    domain = [('street', '=', delivery.unload_address)]
                    existing_address = self.env['panexlogi.address'].search(domain)
                    if not existing_address:
                        unload_address = self.env['panexlogi.address'].create({
                            'is_warehouse': False,
                            'warehouse': False,
                            'is_terminal': False,
                            'terminal': False,
                            'street': delivery.unload_address,
                            'company_name': delivery.unload_company_name,
                            'country': delivery.unload_country.id,
                            'city': delivery.unload_city,
                            'postcode': delivery.unload_postcode,
                        })
                        _logger.info(f"Created unload address: {unload_address.street}")
                        for rec in delivery.deliverydetatilids:
                            if not rec.unload_address:
                                rec.write({
                                    'unload_address': unload_address.id,
                                })
        except Exception as e:
            _logger.error(f"Error in _cron_create_addresses: {str(e)}")


class DeliveryDetail(models.Model):
    _name = 'panexlogi.delivery.detail'
    _description = 'panexlogi.delivery.detail'
    _inherit = ["mail.thread", "mail.activity.mixin"]

    cntrno = fields.Char('Cantainer No')

    loading_ref = fields.Char(string='Loading Ref')
    load_address = fields.Many2one('panexlogi.address', 'Load Address')
    load_condition = fields.Many2one('panexlogi.loadingcondition', 'Load Condition')
    load_date = fields.Datetime(string='Load Date')
    load_timeslot = fields.Char('Unload Timeslot')
    consignee_ref = fields.Char(string='Consignee Ref')
    unload_condition = fields.Many2one('panexlogi.loadingcondition', 'Unload Condition')
    unload_address = fields.Many2one('panexlogi.address', 'Unload Address')
    unload_timeslot = fields.Char('Unload Timeslot')
    unload_date = fields.Datetime(string='Unload Date')

    product = fields.Many2one('product.product', 'Product')
    product_name = fields.Char('Product Name', related='product.name', readonly=True)
    pallets = fields.Float('Palltes', default=1)
    qty = fields.Float('Pcs', default=1)
    batch_no = fields.Char('Batch No')
    model_type = fields.Char('Model Type')
    package_type = fields.Many2one('panexlogi.packagetype', 'Package Type')
    package_size = fields.Char('Size L*W*H')
    weight_per_unit = fields.Float('Weight PER Unit')
    gross_weight = fields.Float('Gross Weight')
    uncode = fields.Char('UN CODE')
    class_no = fields.Char('Class')
    deliveryid = fields.Many2one('panexlogi.delivery', 'Delivery ID')
    # 2025018 wangpeng 是否是ADR goods. 点是的话，就必须要填Uncode。 点选否的话，就不用必填UN code.
    adr = fields.Boolean(string='ADR')
    remark = fields.Text('Remark')
    quote = fields.Float('Quote', default=0)  # 报价
    additional_cost = fields.Float('Additional Cost', default=0)  # 额外费用
    extra_cost = fields.Float('Extra Cost', default=0)  # 额外费用
    state = fields.Selection(
        selection=[
            ('new', 'New'),
            ('approve', 'Approve'),
            ('reject', 'Reject'),
            ('cancel', 'Cancel'),
            ('order', 'Order'),
        ],
        default='new',
        string="State",
        tracking=True
    )
    delivery_order_id = fields.Many2one('panexlogi.delivery.order', string='Delivery Order')
    waybill_detail_id = fields.Many2one('panexlogi.waybill.details', string='Waybill Detail ID')
    delivery_detail_cmr_id = fields.Many2one('panexlogi.delivery.detail.cmr', string='CMR ID')

    # check is adr then uncode is required
    @api.constrains('adr', 'uncode')
    def _check_uncode_required(self):
        for record in self:
            if record.adr and not record.uncode:
                raise ValidationError(_("UN CODE is required when ADR is true."))

    """
    # check that either loading_ref or cntrno is required
    @api.constrains('loading_ref', 'cntrno')
    def _check_loading_ref_or_cntrno(self):
        for record in self:
            if not record.loading_ref and not record.cntrno:
                raise ValidationError(_("Either Loading Ref or Container No is required."))
    """

    def cancel_delivery_detail(self):
        for rec in self:
            if rec.delivery_order_id:
                raise UserError(_("This record is linked to a delivery order and cannot be canceled."))
            else:
                rec.state = 'cancel'
                return True


class DeliveryStatus(models.Model):
    _name = 'panexlogi.delivery.status'
    _description = 'panexlogi.delivery.status'
    _inherit = ["mail.thread", "mail.activity.mixin"]

    delivery_id = fields.Many2one('panexlogi.delivery', 'Delivery ID')
    date = fields.Datetime('Date', default=fields.Datetime.now(), tracking=True)
    extra_cost = fields.Float('Extra Cost', default=0)
    status = fields.Char('Status', tracking=True)
    description = fields.Text('Description')


class DeliveryStatusWizard(models.TransientModel):
    _name = 'panexlogi.delivery.status.wizard'
    _description = 'panexlogi.delivery.status.wizard'

    date = fields.Datetime('Date', default=fields.Datetime.now())
    extra_cost = fields.Float('Extra Cost', default=0)
    status = fields.Selection(
        selection=[
            ('order', 'Order Placed'),
            ('transit', 'In Transit'),
            ('delivery', 'Delivered'),
            ('cancel', 'Cancel'),
            ('return', 'Return'),
            ('other', 'Other'),
            ('complete', 'Complete'),
        ],
        default='order',
        string='status',
        tracking=True
    )
    description = fields.Text('Description')

    def add_line(self):
        self.env['panexlogi.delivery.status'].sudo().create({
            'date': self.date,
            'status': self.status,
            'extra_cost': self.extra_cost,
            'description': self.description,
            'delivery_id': self.env.context.get('active_id'),
        })
        domain = []
        domain.append(('id', '=', self.env.context.get('active_id')))
        self.env['panexlogi.delivery'].sudo().search(domain)._get_extra_cost()
        self.env['panexlogi.delivery'].sudo().search(domain)._onchange_profit()
        return {'type': 'ir.actions.act_window_close'}


class DeliveryOtherDocs(models.Model):
    _name = 'panexlogi.delivery.otherdocs'
    _description = 'panexlogi.delivery.otherdocs'

    description = fields.Text(string='Description')
    file = fields.Binary(string='File')
    filename = fields.Char(string='File name')
    billno = fields.Many2one('panexlogi.delivery', string='Delivery ID')


# Add this after DeliveryDetail class
class DeliveryDetailWizard(models.TransientModel):
    _name = 'panexlogi.delivery.detail.wizard'
    _description = 'Delivery Detail Selection Wizard'

    is_merge = fields.Boolean(string='Merge', default=False)
    delivery_id = fields.Many2one(
        'panexlogi.delivery',
        string='Delivery',
        required=True,
        default=lambda self: self.env.context.get('active_id')
    )

    detail_ids = fields.Many2many(
        'panexlogi.delivery.detail',
        string='Select Details',
        domain="""[
            ('deliveryid', '=', delivery_id),
            ('state', '=', 'approve'),
            ('delivery_order_id', '=', False)
        ]"""
    )

    def action_create_orders(self):
        if not self.detail_ids:
            raise UserError(_("Please select at least one detail record to process."))

        Delivery = self.env['panexlogi.delivery']
        if self.is_merge:  # Merge multiple details into one order
            Delivery._create_single_delivery_order(self.detail_ids)
        else:  # Create one order per detail
            for detail in self.detail_ids:
                Delivery._create_single_delivery_order([detail])

        # Update main delivery state if all details processed
        main_delivery = self.delivery_id
        if all(d.state == 'order' for d in main_delivery.deliverydetatilids):
            main_delivery.state = 'order'

        return {'type': 'ir.actions.act_window_close'}


#  Batch Edit Delivery Details
class DeliveryDetailBatchEditWizard(models.TransientModel):
    _name = 'panexlogi.delivery.detail.batch.edit.wizard'
    _description = 'Batch Edit Delivery Details'

    delivery_id = fields.Many2one('panexlogi.delivery', string='Transport Order')
    detail_ids = fields.Many2many(
        'panexlogi.delivery.detail',
        string='Details',
        domain="[('deliveryid', '=', delivery_id)]",
        relation='delivery_request_batch_edit_details_rel'  # Shorter table name
    )

    loading_ref = fields.Char(string='Loading Ref')
    load_address = fields.Many2one('panexlogi.address', string='Load Address')
    load_condition = fields.Many2one('panexlogi.loadingcondition', string='Load Condition')
    load_date = fields.Datetime(string='Load Date')
    load_timeslot = fields.Char(string='Load Timeslot')
    consignee_ref = fields.Char(string='Consignee Ref')
    unload_condition = fields.Many2one('panexlogi.loadingcondition', string='Unload Condition')
    unload_address = fields.Many2one('panexlogi.address', string='Unload Address')
    unload_timeslot = fields.Char(string='Unload Timeslot')
    unload_date = fields.Datetime(string='Unload Date')

    def apply_changes(self):
        for rec in self:
            for detail in rec.detail_ids:
                if rec.loading_ref:
                    detail.loading_ref = rec.loading_ref
                if rec.load_address:
                    detail.load_address = rec.load_address.id
                if rec.load_condition:
                    detail.load_condition = rec.load_condition.id
                if rec.load_date:
                    detail.load_date = rec.load_date
                if rec.load_timeslot:
                    detail.load_timeslot = rec.load_timeslot
                if rec.consignee_ref:
                    detail.consignee_ref = rec.consignee_ref
                if rec.unload_condition:
                    detail.unload_condition = rec.unload_condition.id
                if rec.unload_address:
                    detail.unload_address = rec.unload_address.id
                if rec.unload_timeslot:
                    detail.unload_timeslot = rec.unload_timeslot
                if rec.unload_date:
                    detail.unload_date = rec.unload_date
        return {'type': 'ir.actions.act_window_close'}


# Delivery CMR file
class DeliveryDatailCmr(models.Model):
    _name = 'panexlogi.delivery.detail.cmr'
    _description = 'panexlogi.delivery.detail.cmr'
    _rec_name = 'billno'

    billno = fields.Char(string='BillNo', readonly=True)
    delivery_detail_id = fields.Many2one('panexlogi.delivery.detail', string='Delivery Detail ID')
    loading_refs = fields.Char(string='Loading Refs')
    load_date = fields.Datetime(string='Loading Date')
    consignee_refs = fields.Char(string='Consignee Refs')
    unload_date = fields.Datetime(string='Unloading Date')
    cntrnos = fields.Char(string='Container Numbers')
    cmr_file = fields.Binary(string='CMR File')
    cmr_filename = fields.Char(string='CMR File name')
    cmr_remark = fields.Text(string='CMR Remark')
    delivery_id = fields.Many2one('panexlogi.delivery', string='Delivery ID')
    delivery_detail_ids = fields.One2many('panexlogi.delivery.detail', 'delivery_detail_cmr_id',
                                          string='Delivery Detail IDs')
    state = fields.Selection(
        selection=[('new', 'New'), ('confirm', 'Confirm'), ('cancel', 'Cancel'), ('order', 'Order')], default='new',
        string="State", tracking=True)

    @api.model
    def create(self, vals):
        if 'delivery_id' in vals:
            delivery = self.env['panexlogi.delivery'].browse(vals['delivery_id'])
            if delivery and delivery.billno:
                # Get existing records for the same delivery_id
                existing_cmr_records = self.search([('delivery_id', '=', delivery.id)])
                # Calculate the next sequence number
                sequence_number = len(existing_cmr_records) + 1
                # Format the sequence as 3 digits (e.g., 001, 002)
                sequence_str = f"{sequence_number:03d}"
                # Combine delivery_id.billno with the sequence
                vals['billno'] = f"{delivery.billno}-{sequence_str}"
        return super(DeliveryDatailCmr, self).create(vals)

    def action_confirm(self):
        for rec in self:
            if rec.state != 'new':
                raise UserError(_("You only can confirm New CMR"))
            else:
                rec.state = 'confirm'
                return True

    def action_cancel(self):
        for rec in self:
            if rec.state != 'new':
                raise UserError(_("You only can cancel New CMR"))
            else:
                # reset delivery_detail_cmr_id
                for detail in rec.delivery_detail_ids:
                    detail.delivery_detail_cmr_id = False
                rec.state = 'cancel'
                return True

    def action_unconfirm(self):
        for rec in self:
            if rec.state != 'confirm':
                raise UserError(_("You only can unconfirm Confirmed CMR"))
            else:
                rec.state = 'new'
                return True


class DeliveryDetailCmrWizard(models.TransientModel):
    _name = 'panexlogi.delivery.detail.cmr.wizard'
    _description = 'panexlogi.delivery.detail.cmr.wizard'

    delivery_id = fields.Many2one(
        'panexlogi.delivery',
        string='Delivery',
        required=True,
        default=lambda self: self.env.context.get('active_id')
    )
    detail_ids = fields.Many2many(
        'panexlogi.delivery.detail',
        string='Delivery Details',
        domain="[('deliveryid', '=', delivery_id), ('delivery_detail_cmr_id', '=', False), ('state', '=', 'approve')]",
        relation='delivery_detail_cmr_wizard_rel'  # Shorter table name
    )
    cmr_remark = fields.Text(string='CMR Remark')

    def action_create_cmr(self):
        if not self.detail_ids:
            raise UserError(_("Please select at least one delivery detail to create a CMR."))
        try:
            # generate CMR file and file_name
            template_record = self.env['panexlogi.excel.template'].search([('type', '=', 'delivery')], limit=1)
            if not template_record:
                raise UserError(_('Template not found!'))
            template_data = base64.b64decode(template_record.template_file)
            template_buffer = BytesIO(template_data)
            # Load the template workbook
            workbook = openpyxl.load_workbook(template_buffer)
            worksheet = workbook.active

            # Write data to the specified cells

            # Alignment styles for Excel cells
            ALIGN_TOP_RIGHT = Alignment(
                vertical="top",  # Align text to the top vertically
                horizontal="right",  # Align text to the right horizontally
                wrap_text=True  # Enable text wrapping
            )

            ALIGN_TOP_LEFT = Alignment(
                vertical="top",  # Align text to the top vertically
                horizontal="left",  # Align text to the left horizontally
                wrap_text=True  # Enable text wrapping
            )

            # Black font
            ARIAL_10 = Font(name='Arial', size=10, color='000000')

            unload_address = []
            if self.detail_ids[0].unload_address.company_name:
                unload_address.append(self.detail_ids[0].unload_address.company_name)
            if self.detail_ids[0].unload_address.street:
                unload_address.append(self.detail_ids[0].unload_address.street)
            if self.detail_ids[0].unload_address.postcode:
                unload_address.append(self.detail_ids[0].unload_address.postcode)
            if self.detail_ids[0].unload_address.country:
                unload_address.append(self.detail_ids[0].unload_address.country.name)

            worksheet['B13'] = ''
            worksheet['B13'] = ', '.join(unload_address)
            worksheet['B20'] = ''
            worksheet['B20'] = self.detail_ids[0].load_address.street
            worksheet['B21'] = ''
            worksheet['B21'] = self.detail_ids[0].load_address.country.name

            worksheet['D21'] = ''
            worksheet['D21'] = fields.Date.today().strftime('  -   -%Y  (DD-MM-YYYY)')  # --2025

            # Fix 1: Convert batch numbers
            batch_nos = [
                str(detail.batch_no) if detail.batch_no and str(detail.batch_no).lower() != 'false'
                else ''
                for detail in self.detail_ids
            ]
            worksheet['B29'] = ''
            worksheet['B29'] = '\n'.join(batch_nos) if batch_nos else ''
            cell = worksheet['B29']
            cell.alignment = ALIGN_TOP_LEFT
            cell.font = ARIAL_10

            # Fix 2: Convert container numbers
            cntrnos = [
                str(detail.cntrno) if detail.cntrno and str(detail.cntrno).lower() != 'false'
                else ''
                for detail in self.detail_ids
            ]
            worksheet['D29'] = ''
            worksheet['D29'] = '\n'.join(cntrnos) if cntrnos else ''
            cell = worksheet['D29']
            cell.alignment = ALIGN_TOP_LEFT
            cell.font = ARIAL_10

            # Fix 3: Convert model types
            model_types = [
                str(detail.model_type) if detail.model_type and str(detail.model_type).lower() != 'false'
                else ''
                for detail in self.detail_ids
            ]
            worksheet['F29'] = ''
            worksheet['F29'] = '\n'.join(model_types) if model_types else ''
            cell = worksheet['F29']
            cell.alignment = ALIGN_TOP_LEFT
            cell.font = ARIAL_10

            pallets = []
            pcs = []
            weights = []
            for detail in self.detail_ids:
                # 直接记录原始值，不需要分割
                if detail.pallets:
                    pallets.append(str(detail.pallets))  # 转换为字符串
                if detail.qty:
                    pcs.append(str(detail.qty))
                if detail.gross_weight:
                    weights.append(str(detail.gross_weight))

            worksheet['H29'] = ''
            worksheet['H29'] = DeliveryDetailCmrWizard.format_multi_line(pallets)
            cell = worksheet['H29']
            cell.alignment = ALIGN_TOP_RIGHT
            cell.font = ARIAL_10

            worksheet['I29'] = ''
            worksheet['I29'] = DeliveryDetailCmrWizard.format_multi_line(pcs)
            cell = worksheet['I29']
            cell.alignment = ALIGN_TOP_RIGHT
            cell.font = ARIAL_10

            worksheet['J29'] = ''
            worksheet['J29'] = DeliveryDetailCmrWizard.format_multi_line(weights)
            cell = worksheet['J29']
            cell.alignment = ALIGN_TOP_RIGHT
            cell.font = ARIAL_10

            # Ensure all elements in pallets are converted to floats before summing
            total_pallets = sum(float(p) for p in pallets if p) if pallets else 0
            total_pcs = sum(float(p) for p in pcs if p) if pcs else 0
            # total_weights = sum(float(w) for w in weights if w) if weights else 0

            worksheet['G36'] = 'Total Pallets:'
            worksheet['H36'] = ''
            worksheet['H36'] = total_pallets
            cell = worksheet['H36']
            cell.alignment = ALIGN_TOP_RIGHT
            cell.font = ARIAL_10

            worksheet['G37'] = 'Total Pcs:'
            worksheet['H37'] = ''
            worksheet['H37'] = total_pcs
            cell.alignment = ALIGN_TOP_RIGHT
            cell.font = ARIAL_10

            worksheet['B48'] = ''
            worksheet['B48'] = 'Warehouse:' + fields.Date.today().strftime('      -   -%Y  (DD-MM-YYYY)')  # --2025
            # Save the workbook to a BytesIO object
            excel_buffer = BytesIO()
            workbook.save(excel_buffer)
            excel_buffer.seek(0)

            # Create the CMR record
            cmr_vals = {
                'delivery_id': self.delivery_id.id,
                'delivery_detail_ids': [(6, 0, self.detail_ids.ids)],
                'loading_refs': ', '.join(str(ref) for ref in set(self.detail_ids.mapped('loading_ref')) if ref),
                # ', '.join(set(ref for ref in self.detail_ids.mapped('loading_ref') if ref)),
                'load_date': min(
                    date for date in self.detail_ids.mapped('load_date') if date) if self.detail_ids.mapped(
                    'load_date') else False,
                'consignee_refs': ', '.join(str(ref) for ref in set(self.detail_ids.mapped('consignee_ref')) if ref),
                # ', '.join(set(ref for ref in self.detail_ids.mapped('consignee_ref') if ref)),
                'unload_date': min(
                    date for date in self.detail_ids.mapped('unload_date') if date) if self.detail_ids.mapped(
                    'unload_date') else False,
                'cntrnos': ', '.join(str(cntr) for cntr in set(self.detail_ids.mapped('cntrno')) if cntr),
                # ', '.join(set(cntr for cntr in self.detail_ids.mapped('cntrno') if cntr)),
                'cmr_file': base64.b64encode(excel_buffer.getvalue()),
                # 'cmr_filename': f'CMR_{self.delivery_id.billno}.xlsx',
                'cmr_remark': self.cmr_remark,
            }
            cmr = self.env['panexlogi.delivery.detail.cmr'].create(cmr_vals)
            cmr.write({'cmr_filename': f'CMR_{cmr.billno}.xlsx'})
            # Link the selected details to the created CMR
            self.detail_ids.write({'delivery_detail_cmr_id': cmr.id})

        except Exception as e:
            raise UserError(_("Error creating CMR: %s") % str(e))

        # return {'type': 'ir.actions.act_window_close'}
        # return a success message
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': 'CMR Created Successfully!',
                'type': 'success',
                'sticky': False,
            }
        }

    @staticmethod
    def format_multi_line(values):
        """Process multiple values into a multi-line string."""
        return '\n'.join(str(v) for v in values) if values else ''
