from datetime import datetime, timedelta
import pytz

from odoo import _, models, fields, api, exceptions
from odoo.exceptions import UserError, ValidationError
import logging
import base64
from io import BytesIO
import openpyxl

_logger = logging.getLogger(__name__)


class DeliveryOrderNew(models.Model):
    _name = 'panexlogi.delivery.order.new'
    _description = 'panexlogi.delivery.order.new'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = 'billno'

    billno = fields.Char(string='BillNo', readonly=True)
    date = fields.Date(string='Date', default=fields.Date.today())
    project = fields.Many2one('panexlogi.project', string='Project（项目）', required=True)
    project_code = fields.Char(string='Project Code', related='project.project_code', readonly=True)
    truckco = fields.Many2one('res.partner', string='Truck Co（卡车公司）', required=True)
    truckco_code = fields.Char(string='Truck Co Code', related='truckco.panex_code', readonly=True)
    delivery_id = fields.Many2one('panexlogi.delivery', string='Delivery ID')
    trailer_type = fields.Many2one('panexlogi.trailertype', string='Type of trailer')
    state = fields.Selection([
        ('new', 'New'),
        ('confirm', 'Confirm'),
        ('cancel', 'Cancel')
    ], string='State', default='new', readonly=True, tracking=True)
    delivery_state = fields.Selection([
        ('none', 'None'),
        ('order', 'Order Placed'),
        ('transit', 'In Transit'),
        ('delivery', 'Delivered'),
        ('cancel', 'Cancel'),
        ('return', 'Return'),
        ('other', 'Other'),
        ('complete', 'Complete'),
    ], string='Delivery State', readonly=True, default='none')
    remark = fields.Text(string='Remark')

    client_company = fields.Many2one('res.partner', string='Company',
                              domain="[('is_company', '=', True),('category_id.name', 'ilike', 'company')]")
    contact_person = fields.Char(string='Contact Person', tracking=True)

    # outside_eu, import_file,export_file, transit_file
    order_file = fields.Binary(string='Order File')
    order_filename = fields.Char(string='Order File Name')
    outside_eu = fields.Boolean(string='Outside of EU')
    import_file = fields.Binary(string='Import File')
    import_filename = fields.Char(string='Import File Name')
    export_file = fields.Binary(string='Export File')
    export_filename = fields.Char(string='Export File Name')
    charge = fields.Float('Charge', default=0, tracking=True, readonly=True, compute='_compute_addtion_cost',
                          store=True)
    quote = fields.Float('Quote', default=0, tracking=True, readonly=True, compute='_compute_addtion_cost', store=True)
    additional_cost = fields.Float('Additional Cost', default=0, tracking=True, readonly=True)  # 额外费用
    extra_cost = fields.Float('Extra Cost', default=0, tracking=True, readonly=True)
    delivery_detail_cmr_ids = fields.Many2many(
        'panexlogi.delivery.detail.cmr',
        'delivery_detail_cmr_rel',
        'delivery_order_id',
        'cmr_detail_id',
        string='CMR Details'
    )

    delivery_detail_ids = fields.Many2many(
        'panexlogi.delivery.detail',
        'delivery_detail_rel',
        'delivery_order_id',
        'detail_id',
        string='Delivery Details'
    )

    delivery_order_change_log_ids = fields.One2many('delivery.order.change.log.new', 'delivery_order_id_new',
                                                    string='Change Log')

    # Properly define company_id and exclude from tracking
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        tracking=False  # Explicitly disable tracking
    )

    @api.model
    def create(self, values):
        """
            生成订单号
        """
        times = fields.Date.today()
        values['billno'] = self.env['ir.sequence'].next_by_code('seq.delivery.order', times)
        delivery_request = super(DeliveryOrderNew, self).create(values)
        return delivery_request

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
                for line in rec.delivery_detail_cmr_ids:
                    line.delivery_order_new_id = False
                    line.state = 'confirm'

                return True

    def action_print_delivery_order(self):
        # Generate PDF using standard reporting method
        from odoo import _
        try:
            self.ensure_one()
            for rec in self:
                rec.write({
                    'order_file': False,
                    'order_filename': False
                })

                # Get predefined report reference
                report = self.env['ir.actions.report'].search([
                    ('report_name', '=', 'panexLogi.report_delivery_order_my')
                ], limit=1)

                # Force template reload and generate PDF
                self.env.flush_all()

                # Use standard rendering method
                result = report._render_qweb_pdf(report_ref=report.report_name,
                                                 res_ids=[rec.id],
                                                 data=None)

                # Validate return structure
                if not isinstance(result, tuple) or len(result) < 1:
                    raise ValueError("Invalid data structure returned from report rendering")

                pdf_content = result[0]

                # Create attachment
                order_file = self.env['ir.attachment'].create({
                    'name': f'Delivery_Order_{self.billno}_{fields.Datetime.now().strftime("%Y%m%d%H%M%S")}.pdf',
                    'type': 'binary',
                    'datas': base64.b64encode(pdf_content),
                    'res_model': self._name,
                    'res_id': rec.id,
                })
                # Write the attachment to the record
                rec.write({
                    'order_file': order_file.datas,
                    'order_filename': order_file.name
                })

        except Exception as e:
            _logger.error("PDF generate failed: %s", str(e))
            raise UserError(_("PDF generate failed: %s") % str(e))

    @api.depends('delivery_order_change_log_ids.extra_cost', 'delivery_order_change_log_ids.charge')
    def _compute_addtion_cost(self):
        for record in self:
            # Reset to the original value
            original_extra_cost = record._origin.extra_cost or 0
            original_charge = record._origin.charge or 0

            # Start with the original values
            record.extra_cost = original_extra_cost
            record.charge = original_charge

            # Add values from related records
            for log in record.delivery_order_change_log_ids:
                record.extra_cost += log.extra_cost
                record.charge += log.charge

    # The method returns an action dictionary that opens the delivery.order.new.wizard in a form view
    def action_open_change_wizard(self, **kwargs):
        """Open the Change Wizard for the current record."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Change Log',
            'res_model': 'delivery.order.change.wizard.new',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_delivery_order_id_new': self.id,
            },
        }


class DeliveryOrderChangeLogNew(models.Model):
    _name = 'delivery.order.change.log.new'
    _description = 'Delivery Order Change Log'

    delivery_order_id_new = fields.Many2one(
        'panexlogi.delivery.order.new',
        string='Delivery Order',
        ondelete='cascade',
        required=True,
        readonly=True,
    )
    extra_cost = fields.Float(string='Extra Cost')
    charge = fields.Float(string='Charge')
    reason = fields.Text(string='Reason')
    remark = fields.Text(string='Remark')
    change_time = fields.Datetime(string='Change Time', default=fields.Datetime.now)


class DeliveryOrderChangeWizardNew(models.TransientModel):
    _name = 'delivery.order.change.wizard.new'
    _description = 'Delivery Order Change Wizard'

    delivery_order_id_new = fields.Many2one(
        'panexlogi.delivery.order.new',
        string='New Delivery Order',
        ondelete='cascade',
        readonly=True,
    )
    extra_cost = fields.Float(string='Extra Cost (add)')
    charge = fields.Float(string='Charge (add)')
    reason = fields.Text(string='Reason')
    remark = fields.Text(string='Remark')

    def action_record_change(self):
        """Record the change and log it in a history model."""
        self.env['delivery.order.change.log.new'].create({
            'delivery_order_id_new': self.delivery_order_id_new.id,
            'extra_cost': self.extra_cost,
            'charge': self.charge,
            'reason': self.reason,
            'remark': self.remark,
            'change_time': fields.Datetime.now(),
        })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': 'Change recorded successfully!',
                'type': 'success',
                'sticky': False,
            }
        }, {
            'type': 'ir.actions.act_window_close'
        }
