from datetime import datetime, timedelta
import pytz

from odoo import _, models, fields, api, exceptions
from odoo.exceptions import UserError, ValidationError
import logging
import base64

_logger = logging.getLogger(__name__)


# 配送订单
class DeliveryOrder(models.Model):
    _name = 'panexlogi.delivery.order'
    _description = 'panexlogi.delivery.order'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = 'billno'

    billno = fields.Char(string='BillNo', readonly=True)
    date = fields.Date(string='Date', default=fields.Date.today())
    project = fields.Many2one('panexlogi.project', string='Project（项目）', required=True)
    project_code = fields.Char(string='Project Code', related='project.project_code', readonly=True)
    truckco = fields.Many2one('res.partner', string='Truck Co（卡车公司）', required=True)
    truckco_code = fields.Char(string='Truck Co Code', related='truckco.panex_code', readonly=True)
    delivery_id = fields.Many2one('panexlogi.delivery', string='Delivery ID', required=True)
    delivery_detail_id = fields.Many2one('panexlogi.delivery.detail', string='Delivery Detail ID', required=True)
    trailer_type = fields.Many2one('panexlogi.trailertype', string='Type of trailer')
    state = fields.Selection([
        ('new', 'New'),
        ('confirm', 'Confirm'),
        ('cancel', 'Cancel')
    ], string='State', default='new', tracking=True)
    delivery_state = fields.Selection([
        ('none', 'None'),
        ('order', 'Order Placed'),
        ('transit', 'In Transit'),
        ('delivery', 'Delivered'),
        ('cancel', 'Cancel'),
        ('return', 'Return'),
        ('other', 'Other'),
        ('complete', 'Complete'),
    ], string='Delivery State', related='delivery_detail_id.state', readonly=True, default='none')

    load_address = fields.Char(string='Address')
    load_company_name = fields.Char(string='Company Name')
    load_contact_phone = fields.Char(string='Contact Phone')
    load_postcode = fields.Char(string='Postcode')
    load_country = fields.Many2one('res.country', 'Load Country')
    load_country_code = fields.Char('Country Code', related='load_country.code')
    load_address_timeslot = fields.Char('Timeslot')
    unload_address = fields.Char(string='Address')
    unload_company_name = fields.Char(string='Company Name')
    unload_contact_phone = fields.Char(string='Contact Phone')
    unload_postcode = fields.Char(string='Postcode')
    unload_country = fields.Many2one('res.country', 'Unload Country')
    unload_country_code = fields.Char('Country Code', related='unload_country.code')
    unload_address_timeslot = fields.Char('Timeslot')

    delivery_type = fields.Many2one('panexlogi.deliverytype', 'Delivery Type')
    loading_ref = fields.Char(string='Loading Ref')
    unloading_ref = fields.Char(string='Unloading Ref')
    loading_conditon = fields.Many2one('panexlogi.loadingcondition', 'Condition')
    unloading_conditon = fields.Many2one('panexlogi.loadingcondition', 'Condition')
    planned_for_loading = fields.Datetime(string='Planned Loading')
    planned_for_unloading = fields.Datetime(string='Planned Unloading')

    cntrno = fields.Char('Container No')
    product = fields.Many2one('product.product', 'Product')
    product_name = fields.Char('Product Name', related='product.name')
    qty = fields.Float('Quantity', default=1)
    package_type = fields.Many2one('panexlogi.packagetype', 'Package Type')
    package_size = fields.Char('Size L*W*H')
    weight_per_unit = fields.Float('Weight PER Unit')
    gross_weight = fields.Float('Gross Weight')
    uncode = fields.Char('UN CODE')
    class_no = fields.Char('Class')
    adr = fields.Boolean(string='ADR')
    remark = fields.Text('Remark')
    order_remark = fields.Text('Order Remark', tracking='1')
    load_remark = fields.Text('Load Remark', tracking='1')
    unload_remark = fields.Text('Unload Remark', tracking='1')
    quote = fields.Float('Quote', default=0)  # 报价

    pod_file = fields.Binary(string='POD File')
    pod_filename = fields.Char(string='POD File Name')
    order_file = fields.Binary(string='Order File')
    order_filename = fields.Char(string='Order File Name')

    client = fields.Char('Client', default='WD Europe')
    contact_person = fields.Char('Contact Person', default='Cris +31627283491')

    @api.model
    def create(self, values):
        """
            生成订单号
        """
        times = fields.Date.today()
        values['billno'] = self.env['ir.sequence'].next_by_code('seq.delivery.order', times)
        delivery_request = super(DeliveryOrder, self).create(values)
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
                rec.delivery_detail_id.delivery_order_id = False
                rec.delivery_detail_id.state = 'approve'
                rec.state = 'cancel'
                rec.delivery_id.state = 'confirm'
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

    def action_print_delivery_order_tree(self):
        try:
            selected_orders = self.browse(self.env.context.get('active_ids'))

            # Ensure at least one record is selected
            if not selected_orders:
                raise UserError("Please select at least one Delivery Order.")

            # Generate PDF for each selected order
            for order in selected_orders:
                if order.state != 'confirm':
                    raise UserError(_("You only can print Confirm Order"))

            for order in selected_orders:
                order.action_print_delivery_order_tree()
            # return a seccuess message
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('PDF generated successfully!'),
                    'sticky': False,
                },
            }


        except Exception as e:
            _logger.error("PDF generation failed: %s", str(e))
            raise UserError(_("PDF generation error: %s") % str(e))


class DeliveryOrderLine(models.Model):
    _name = 'panexlogi.delivery.order.line'
    _description = 'panexlogi.delivery.order.line'
    _rec_name = 'billno'

    billno = fields.Char(string='BillNo', readonly=True)

    loading_ref = fields.Char(string='Loading Ref')
    consignee_ref = fields.Char(string='Consignee Ref')

    delivery_type = fields.Many2one('panexlogi.deliverytype', 'Delivery Type')
    loading_conditon = fields.Many2one('panexlogi.loadingcondition', ' Condition')
    unloading_conditon = fields.Many2one('panexlogi.loadingcondition', 'Condition')
    planned_for_loading = fields.Datetime(string='Planned Loading')
    planned_for_unloading = fields.Datetime(string='Planned Unloading')

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
    adr = fields.Boolean(string='ADR')
    remark = fields.Text('Remark', tracking='1')

    quote = fields.Float('Quote', default=0)  # 报价

    delivery_order_id = fields.Many2one('panexlogi.delivery.order', string='Delivery Order')

    state = fields.Selection([
        ('new', 'New'),
        ('order', 'Order Placed'),
        ('transit', 'In Transit'),
        ('delivery', 'Delivered'),
        ('cancel', 'Cancel'),
        ('return', 'Return'),
        ('other', 'Other'),
        ('complete', 'Complete')], string='Status', default='new', tracking='1')

    pod_file = fields.Binary(string='POD File')
    pod_filename = fields.Char(string='POD File Name')
    order_file = fields.Binary(string='Order File')
    order_filename = fields.Char(string='Order File Name')

    @api.model
    def create(self, values):
        """
            生成订单号
        """
        times = fields.Date.today()
        values['billno'] = self.env['ir.sequence'].next_by_code('seq.delivery.order.line', times)
        delivery_request = super(DeliveryOrderLine, self).create(values)
        return delivery_request
