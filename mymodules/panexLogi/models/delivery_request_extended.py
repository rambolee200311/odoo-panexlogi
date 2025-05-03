from odoo import _, models, fields, api
from odoo.exceptions import UserError
import logging
import base64
import re
from lxml import etree

_logger = logging.getLogger(__name__)


class DeliveryExtended(models.Model):
    _inherit = 'panexlogi.delivery'
    _description = 'panexlogi.delivery.extended'

    quote_content = fields.Text(string='Content',
                                default='Please provide your quotation for the following delivery requests:')
    # For quote_receiver
    quote_receiver = fields.Many2many(
        'res.partner',
        relation='delivery_quote_receiver_rel',  # Unique table name
        column1='delivery_id',  # This record's ID
        column2='partner_id',  # Partner's ID
        string='Truck Co',
        domain=[('truck', '=', True), ('email', '!=', False)]
    )
    quote_receiver_email = fields.Char(string='Receiver Email', compute='_compute_receiver_email_to')
    delivery_quote_email_log_ids = fields.One2many('delivery.quote.email.log', 'delivery_id',
                                                   string='Quote Emails')

    @api.depends('inform_receiver')
    def _compute_receiver_email_to(self):
        for record in self:
            # Filter partners with valid emails
            valid_partners = record.quote_receiver.filtered(lambda p: p.email)
            emails = valid_partners.mapped('email')
            record.quote_receiver_email = ', '.join(emails) if emails else False  # Set to False if empty
            _logger.debug('Computed quote_receiver_email: %s', record.quote_receiver_email)

    def get_grouped_requests(self):
        """Group delivery request details by load_address and unload_address."""
        self.ensure_one()
        groups = {}
        for line in self.deliverydetatilids:
            key = (line.load_address.id, line.unload_address.id)  # Group by load and unload addresses
            groups.setdefault(key, []).append(line)
        return groups.values()

    def sanitize_email(self, email):
        """Sanitize email to remove invalid characters."""
        if email:
            # Remove linefeed, carriage return, and other control characters
            email = re.sub(r'[\n\r\t\x00-\x1f\x7f-\x9f]', '', email).strip()
        return email

    def get_email_context(self, company):
        """Prepare the context for the email template for a specific receiver."""
        self.ensure_one()
        # 使用当前配送订单的公司 logo
        logo = self.env.user.company_id.logo
        logo_base64 = base64.b64encode(logo).decode('utf-8') if logo and isinstance(logo, bytes) else None
        quote_content = self.quote_content or 'Please provide your quotation for the following delivery requests:'
        grouped_requests = list(self.get_grouped_requests())
        billno = self.billno or 'UNKNOWN'  # Provide a default value if billno is None
        delivery_type= self.delivery_type.deliverytype_name or 'UNKNOWN'  # Provide a default value if delivery_type is None

        _logger.info('Grouped requests: %s', grouped_requests)
        _logger.info('receiver_name: %s', company.name.strip())
        _logger.info('receiver_email: %s', company.email.strip())
        _logger.info('quote_content: %s', quote_content)

        return {
            'receiver_name': company.name.strip(),
            'receiver_email': company.email.strip(),
            'quote_content': quote_content,
            'grouped_requests': grouped_requests,
            'company_logo': logo_base64,
            'billno': billno,
            'user': self.env.user,
            'delivery_type': delivery_type,
            # 添加父模型数据（如需要）
            # 'delivery_order': self,
        }

    def action_send_quotes(self):
        """Send quote emails to all selected truck companies."""
        self.ensure_one()

        """Send the quote email to the specified receivers using the given template."""
        template = self.env.ref('panexLogi.email_template_delivery_quote')

        for company in self.quote_receiver.filtered(lambda c: c.email):
            try:
                receiver_context = self.get_email_context(company)
                email = self.sanitize_email(company.email)
                # Manually render the email subject and body with context
                subject = template.with_context(**receiver_context)._render_template(
                    template.subject, 'panexlogi.delivery', [self.id]
                ).get(self.id)

                # Parse the body_html template into an etree object
                body_html_etree = etree.fromstring(template.body_html)

                # Render the email body using ir.ui.view
                body_html = self.env['ir.ui.view']._render_template(body_html_etree, receiver_context)

                _logger.info('Rendered email body: %s', body_html)
                # Create and send the email directly
                mail = self.env['mail.mail'].create({
                    'subject': subject,
                    'body_html': body_html,
                    'email_to': email,
                    'email_from': self.env.user.email_formatted,
                })
                mail.send()

                # Log the email sending result
                self.env['delivery.quote.email.log'].create({
                    'delivery_id': self.id,
                    'email_to': email,
                    'email_sent': True,
                    'email_date': fields.Datetime.now(),
                    'email_body': body_html,
                    'email_result': 'Email sent successfully'
                })
            except Exception as e:
                self.env['delivery.quote.email.log'].create({
                    'delivery_id': self.id,
                    'email_to': email,
                    'email_sent': False,
                    'email_date': fields.Datetime.now(),
                    'email_body': '',
                    'email_result': str(e)
                })
                _logger.warning('Error sending email to %s: %s', email, str(e))
    #    # The method returns an action dictionary that opens the delivery.order.new.wizard in a form view
    def action_open_delivery_order_new_wizard(self):
        """Open the wizard to create a new Delivery Order."""
        return {
            'name': _('Create Delivery Order New'),
            'type': 'ir.actions.act_window',
            'res_model': 'delivery.order.new.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_delivery_id': self.id,
                'active_id': self.id
            },
        }
class DeliveryQuoteEmailLog(models.Model):
    _name = 'delivery.quote.email.log'
    _description = 'Delivery Quote Email Log'

    delivery_id = fields.Many2one(
        'panexlogi.delivery',
        string='Delivery Request',
        ondelete='cascade',
        required=True
    )
    email_to = fields.Char(string='Email To')
    email_sent = fields.Boolean(string='Email Sent')
    email_date = fields.Datetime(string='Email Date')
    email_body = fields.Text(string='Email Body')
    email_result = fields.Text(string='Email Result')

class DeliveryOrderNewWizard(models.TransientModel):
    _name = 'delivery.order.new.wizard'
    _description = 'Wizard to Create Delivery Order New'

    delivery_id = fields.Many2one(
        'panexlogi.delivery',
        string="Related Delivery",
        default=lambda self: self.env.context.get('active_id')
    )

    selected_cmr_ids = fields.Many2many(
        'panexlogi.delivery.detail.cmr',
        string='Available CMR Records',
        domain="[('delivery_id', '=', delivery_id), ('state', '=', 'confirm'), ('delivery_order_new_id', '=', False)]"
    )

    def create_delivery_order_new(self):
        if not self.selected_cmr_ids:
            raise UserError(_("Please select at least one CMR Detail."))

        # Prepare values for the new delivery order
        delivery_order_vals = {
            'project': self.selected_cmr_ids[0].delivery_id.project.id,
            'truckco': self.selected_cmr_ids[0].delivery_id.trucker.id,
            'delivery_id': self.selected_cmr_ids[0].delivery_id.id,
            'delivery_detail_cmr_ids': [(6, 0, self.selected_cmr_ids.ids)],
            'delivery_detail_ids': [(6, 0, self.selected_cmr_ids.mapped('delivery_detail_id').ids)],
        }

        # Create the new delivery order
        new_delivery_order = self.env['panexlogi.delivery.order.new'].create(delivery_order_vals)

        # Link the selected CMR details to the new delivery order
        #self.delivery_detail_cmr_ids.write({'delivery_order_new_id': new_delivery_order.id})
        for line in self.selected_cmr_ids:
            line.delivery_order_new_id = new_delivery_order.id


        # Return an action to open the newly created delivery order
        return {
            'name': _('Delivery Order New'),
            'type': 'ir.actions.act_window',
            'res_model': 'panexlogi.delivery.order.new',
            'view_mode': 'form',
            'res_id': new_delivery_order.id,
            'target': 'current',
        }