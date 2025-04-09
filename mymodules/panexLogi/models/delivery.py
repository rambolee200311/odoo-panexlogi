from datetime import datetime, timedelta
import pytz

from odoo import _, models, fields, api, exceptions
from odoo.exceptions import UserError, ValidationError
import logging

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
    load_address = fields.Char(string='Address')
    load_company_name = fields.Char(string='Company Name')
    load_contact_phone = fields.Char(string='Contact Phone')
    load_postcode = fields.Char(string='Postcode')
    load_country = fields.Many2one('res.country', 'Load Coutry')
    load_country_code = fields.Char('Country Code', related='load_country.code')
    load_address_timeslot = fields.Char('Timeslot')
    unload_address = fields.Char(string='Address')
    unload_company_name = fields.Char(string='Company Name')
    unload_contact_phone = fields.Char(string='Contact Phone')
    unload_postcode = fields.Char(string='Postcode')
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

    @api.model
    def _create_single_delivery_order(self, rec):
        try:
            delivery_order_vals = {
                'delivery_detail_id': rec.id,
                'delivery_id': rec.deliveryid.id,
                'project': rec.deliveryid.project.id,
                'truckco': rec.deliveryid.trucker.id,
                'delivery_type': rec.deliveryid.delivery_type.id,
                'loading_ref': rec.loading_ref,
                'unloading_ref': rec.deliveryid.consignee_ref,
                'loading_conditon': rec.deliveryid.loading_conditon.id,
                'unloading_conditon': rec.deliveryid.unloading_conditon.id,
                'planned_for_loading': rec.deliveryid.planned_for_loading,
                'planned_for_unloading': rec.deliveryid.planned_for_unloading,
                'load_address': rec.deliveryid.load_address,
                'load_company_name': rec.deliveryid.load_company_name,
                'load_contact_phone': rec.deliveryid.load_contact_phone,
                'load_postcode': rec.deliveryid.load_postcode,
                'load_country': rec.deliveryid.load_country.id,
                'load_country_code': rec.deliveryid.load_country_code,
                'load_address_timeslot': rec.deliveryid.load_address_timeslot,
                'unload_address': rec.deliveryid.unload_address,
                'unload_company_name': rec.deliveryid.unload_company_name,
                'unload_contact_phone': rec.deliveryid.unload_contact_phone,
                'unload_postcode': rec.deliveryid.unload_postcode,
                'unload_country': rec.deliveryid.unload_country.id,
                'unload_country_code': rec.deliveryid.unload_country_code,
                'unload_address_timeslot': rec.deliveryid.unload_address_timeslot,
                'cntrno': rec.cntrno,
                'product': rec.product.id,
                'qty': rec.qty,
                'package_type': rec.package_type.id,
                'package_size': rec.package_size,
                'weight_per_unit': rec.weight_per_unit,
                'gross_weight': rec.gross_weight,
                'uncode': rec.uncode,
                'class_no': rec.class_no,
                'adr': rec.adr,
                'remark': rec.remark,
                'quote': rec.quote,
            }
            delivery_order = self.env['panexlogi.delivery.order'].create(delivery_order_vals)
            rec.write({
                'state': 'order',
                'delivery_order_id': delivery_order.id
            })

        except Exception as e:
            raise UserError(_("Error creating delivery order: %s") % str(e))


class DeliveryDetail(models.Model):
    _name = 'panexlogi.delivery.detail'
    _description = 'panexlogi.delivery.detail'
    _inherit = ["mail.thread", "mail.activity.mixin"]

    loading_ref = fields.Char(string='Loading Ref')
    cntrno = fields.Char('Cantainer No')
    product = fields.Many2one('product.product', 'Product')
    product_name = fields.Char('Product Name', related='product.name', readonly=True)
    qty = fields.Float('Quantity', default=1)
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
        for detail in self.detail_ids:
            Delivery._create_single_delivery_order(detail)

        # Update main delivery state if all details processed
        main_delivery = self.delivery_id
        if all(d.state == 'order' for d in main_delivery.deliverydetatilids):
            main_delivery.state = 'order'

        return {'type': 'ir.actions.act_window_close'}