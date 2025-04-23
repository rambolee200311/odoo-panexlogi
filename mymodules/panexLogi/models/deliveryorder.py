from datetime import datetime, timedelta
import pytz

from odoo import _, models, fields, api, exceptions
from odoo.exceptions import UserError, ValidationError
import logging
import base64
from io import BytesIO
import openpyxl

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
    delivery_id = fields.Many2one('panexlogi.delivery', string='Delivery ID')
    delivery_detail_id = fields.Many2one('panexlogi.delivery.detail', string='Delivery Detail ID')
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

    # outside_eu, import_file,export_file, transit_file
    outside_eu = fields.Boolean(string='Outside of EU')
    import_file = fields.Binary(string='Import File')
    import_filename = fields.Char(string='Import File Name')
    export_file = fields.Binary(string='Export File')
    export_filename = fields.Char(string='Export File Name')

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

    # load_address = fields.Char(string='Address')
    loading_address = fields.Many2one('panexlogi.address', 'Load Address')
    load_company_name = fields.Char(string='Company Name', related='loading_address.company_name')
    load_contact_phone = fields.Char(string='Contact Phone', related='loading_address.phone')
    load_postcode = fields.Char(string='Postcode', related='loading_address.postcode')
    load_city = fields.Char(string='City', related='loading_address.city')
    load_country = fields.Many2one('res.country', 'Load Country', related='loading_address.country')
    load_country_code = fields.Char('Country Code', related='load_country.code')
    load_address_timeslot = fields.Char('Timeslot')
    # unload_address = fields.Char(string='Address')
    unloading_address = fields.Many2one('panexlogi.address', 'Unload Address')
    unload_company_name = fields.Char(string='Company Name', related='unloading_address.company_name')
    unload_contact_phone = fields.Char(string='Contact Phone', related='unloading_address.phone')
    unload_postcode = fields.Char(string='Postcode', related='unloading_address.postcode')
    unload_city = fields.Char(string='City', related='unloading_address.city')
    unload_country = fields.Many2one('res.country', 'Unload Country', related='unloading_address.country')
    unload_country_code = fields.Char('Country Code', related='unload_country.code')
    unload_address_timeslot = fields.Char('Timeslot')

    delivery_type = fields.Many2one('panexlogi.deliverytype', 'Delivery Type')
    loading_ref = fields.Char(string='Loading Ref')
    unloading_ref = fields.Char(string='Unloading Ref')
    loading_condition = fields.Many2one('panexlogi.loadingcondition', 'Condition')
    unloading_condition = fields.Many2one('panexlogi.loadingcondition', 'Condition')
    planned_for_loading = fields.Datetime(string='Planned Loading')
    planned_for_unloading = fields.Datetime(string='Planned Unloading')

    cntrno = fields.Char('Container No')
    product = fields.Many2one('product.product', 'Product')
    product_name = fields.Char('Product Name', related='product.name')
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
    cmr_file = fields.Binary(string='CMR File')
    cmr_filename = fields.Char(string='CMR File Name')

    client = fields.Char('Client', default='WD Europe')
    contact_person = fields.Char('Contact Person', default='Cris +31627283491')

    cntrnos = fields.Char('Container Nos', compute='_compute_cntrnos', store=True)
    loading_refs = fields.Char(string='Loading Refs', compute='_compute_cntrnos', store=True)
    # delivery_order_line_ids = fields.One2many('panexlogi.delivery.order.line',
    #                                          'delivery_order_id',
    #                                          string='Delivery Order Line')
    delivery_order_line_ids = fields.One2many(
        'panexlogi.delivery.order.line',  # Replace with the correct model name for order lines
        'delivery_order_id',  # Replace with the correct foreign key field in the related model
        string='Delivery Order Lines'
    )

    delivery_order_cmr_line_ids = fields.One2many('panexlogi.delivery.order.cmr.line',
                                                  'delivery_order_id',
                                                  string='Delivery Order CMR Line')
    delivery_order_change_log_ids = fields.One2many(
        'delivery.order.change.log',
        'delivery_order_id',
        string='Change Logs'
    )

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

    @api.depends('delivery_detail_id.cntrno', 'delivery_detail_id.loading_ref')
    def _compute_cntrnos(self):
        """
            Compute container numbers and loading references.
        """
        for rec in self:
            cntrnos = []
            loading_refs = []
            for line in rec.delivery_detail_id:
                # Ensure values are strings, skip if False or None
                if line.cntrno:
                    cntrnos.append(str(line.cntrno))
                if line.loading_ref:
                    loading_refs.append(str(line.loading_ref))
            rec.cntrnos = ', '.join(cntrnos)
            rec.loading_refs = ', '.join(loading_refs)

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
                for line in rec.delivery_order_line_ids:
                    line.delivery_detail_id.delivery_order_id = False
                    line.delivery_detail_id.state = 'approve'
                rec.state = 'cancel'
                # rec.delivery_id.state = 'confirm'
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

    # 生成CMR文件
    def generate_cmr_file(self):
        try:
            template_record = self.env['panexlogi.excel.template'].search([('type', '=', 'delivery')], limit=1)
            # check if the template is em
            if not template_record:
                raise UserError(_('Template not found!'))
            template_data = base64.b64decode(template_record.template_file)
            template_buffer = BytesIO(template_data)
            for rec in self:
                # check if the load_company_name is empty
                if not rec.load_company_name:
                    raise UserError(_('Please fill in the load company name!'))
                # check if the unload_company_name is empty
                if not rec.unload_company_name:
                    raise UserError(_('Please fill in the unload company name!'))
                # check if the load_address is empty
                if not rec.load_address:
                    raise UserError(_('Please fill in the load address!'))
                # check if the unload_address is empty
                if not rec.unload_address:
                    raise UserError(_('Please fill in the unload address!'))

                # receiver = rec.waybill_billno.project.customer.name
                # teminal = rec.collterminal.terminal_name

                # Load the template workbook
                workbook = openpyxl.load_workbook(template_buffer)
                worksheet = workbook.active

                # Write data to the specified cells
                worksheet['B6'] = ''
                worksheet['B6'] = rec.project.project_name if rec.project else ''
                worksheet['B7'] = ''
                worksheet['B7'] = rec.load_comanpy_name + ' ' + rec.load_address
                worksheet['B13'] = ''
                worksheet['B13'] = rec.unload_comanpy_name + ' ' + rec.unload_address
                worksheet['B20'] = ''
                worksheet['B20'] = ''
                worksheet['B21'] = ''
                worksheet['B21'] = rec.load_country.name
                worksheet['D21'] = ''
                worksheet['D21'] = fields.Date.today().strftime('  -   -%Y  (DD-MM-YYYY)')  # --2025
                worksheet['B27'] = ''
                worksheet['B29'] = ''
                worksheet['B29'] = ''
                worksheet['D29'] = ''
                ref = []
                if not rec.cntrno:
                    ref.append(rec.cntrnos)
                if not rec.loading_refs:
                    ref.append(rec.loading_refs)
                ref_fullname = '-'.join(ref)

                worksheet['D29'] = ''
                worksheet['F29'] = ref_fullname
                worksheet['F29'] = rec.product.name if rec.product else ''
                worksheet['H29'] = ''
                worksheet['H29'] = rec.qty if rec.qty else 1
                worksheet['I29'] = ''
                worksheet['I29'] = rec.gross_weight if rec.gross_weight else 0

                worksheet['J28'] = ''
                worksheet['J28'] = 'Pieces'
                worksheet['J29'] = ''
                worksheet['J29'] = rec.qty if rec.qty else 1

                worksheet['B48'] = ''
                worksheet['B48'] = 'warehouse'

                # Save the workbook to a BytesIO object
                excel_buffer = BytesIO()
                workbook.save(excel_buffer)
                excel_buffer.seek(0)
                rec.cmr_file = base64.b64encode(excel_buffer.read())
                rec.cmr_filename = f'CMR_{rec.billno}_{ref_fullname}.xlsx'
            # return a success message
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Success',
                    'message': 'CMR file generated successfully!',
                    'type': 'success',
                    'sticky': False,
                }
            }

        except Exception as e:
            raise UserError(_('Error generating CMR file: %s') % str(e))

    class DeliveryOrder(models.Model):
        _name = 'panexlogi.delivery.order'

        # ... (其他字段保持原样)

    # 生成CMR Lines
    def action_create_cmr_lines(self):
        """ 为每个唯一的 loading_ref + cntrno 组合创建 CMR Line """
        for order in self:

            # 1. 校验 delivery_order_line_ids 是否存在
            if not order.delivery_order_line_ids:
                raise UserError(_("No delivery order lines found!"))

            # 2. 收集所有唯一的 loading_ref + cntrno 组合
            unique_combinations = set()
            for line in order.delivery_order_line_ids:
                if not line.loading_ref or not line.cntrno:
                    raise UserError(
                        _("Line %s has empty Loading Ref or Container No!") % line.billno
                    )
                unique_combinations.add((line.loading_ref, line.cntrno))

            # 3. 为每个组合创建 CMR Line
            cmr_lines = []
            for loading_ref, cntrno in unique_combinations:
                # 查找第一个匹配的 line 获取其他字段值
                reference_line = order.delivery_order_line_ids.filtered(
                    lambda l: l.loading_ref == loading_ref and l.cntrno == cntrno
                )[:1]

                cmr_vals = {
                    'loading_ref': loading_ref,
                    'cntrno': cntrno,
                    '': reference_line.product.id,
                    'qty': reference_line.qty,
                    'gross_weight': reference_line[0].gross_weight,
                    'planned_for_loading': reference_line[0].planned_for_loading,
                    'planned_for_unloading': reference_line[0].planned_for_unloading,
                    # 其他必要字段...
                }
                cmr_lines.append((0, 0, cmr_vals))

            # 4. 批量写入 CMR Lines
            order.write({'delivery_cmr_line_ids': cmr_lines})

            # 返回成功提示
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Success'),
                    'message': _('CMR Lines created for %s unique combinations!') % len(unique_combinations),
                    'type': 'success',
                    'sticky': False,
                }
            }


class DeliveryOrderLine(models.Model):
    _name = 'panexlogi.delivery.order.line'
    _description = 'panexlogi.delivery.order.line'
    _rec_name = 'billno'

    billno = fields.Char(string='BillNo', readonly=True)

    loading_ref = fields.Char(string='Loading Ref')
    consignee_ref = fields.Char(string='Consignee Ref')

    delivery_type = fields.Many2one('panexlogi.deliverytype', 'Delivery Type')
    loading_condition = fields.Many2one('panexlogi.loadingcondition', ' Condition')
    unloading_condition = fields.Many2one('panexlogi.loadingcondition', 'Condition')
    planned_for_loading = fields.Datetime(string='Planned Loading')
    planned_for_unloading = fields.Datetime(string='Planned Unloading')

    cntrno = fields.Char('Container No')
    product = fields.Many2one('product.product', 'Product')
    product_name = fields.Char('Product Name', related='product.name')
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
    adr = fields.Boolean(string='ADR')
    stackable = fields.Boolean(string='Stackable')
    remark = fields.Text('Remark')
    order_remark = fields.Text('Order Remark', tracking='1')
    load_remark = fields.Text('Load Remark', tracking='1')
    unload_remark = fields.Text('Unload Remark', tracking='1')
    quote = fields.Float('Quote', default=0)  # 报价
    additional_cost = fields.Float('Additional Cost', default=0)  # 附加报价

    pod_file = fields.Binary(string='POD File')
    pod_filename = fields.Char(string='POD File Name')
    order_file = fields.Binary(string='Order File')
    order_filename = fields.Char(string='Order File Name')

    # delivery_order_id = fields.Many2one('panexlogi.delivery.order', string='Delivery Order')
    delivery_id = fields.Many2one(
        'panexlogi.delivery',
        string='Delivery',
        ondelete='cascade'
    )
    delivery_order_id = fields.Many2one(
        'panexlogi.delivery.order',
        string='Delivery Order',
        ondelete='cascade'
    )
    delivery_detail_id = fields.Many2one(
        'panexlogi.delivery.detail',
        string='Delivery Detail'
    )
    order_billno = fields.Char(string='Order BillNo', related='delivery_order_id.billno', readonly=True)
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
    # load_address = fields.Char(string='Address')
    load_address = fields.Many2one('panexlogi.address', 'load Address')
    load_company_name = fields.Char(string='Company Name', related='load_address.company_name')
    load_contact_phone = fields.Char(string='Contact Phone', related='load_address.phone')
    load_postcode = fields.Char(string='Postcode', related='load_address.postcode')
    load_city = fields.Char(string='City', related='load_address.city')
    load_country = fields.Many2one('res.country', 'Load Country', related='load_address.country')
    load_country_code = fields.Char('Country Code', related='load_country.code')
    load_address_timeslot = fields.Char('Timeslot')
    # unload_address = fields.Char(string='Address')
    unload_address = fields.Many2one('panexlogi.address', 'Unload Address')
    unload_company_name = fields.Char(string='Company Name', related='unload_address.company_name')
    unload_contact_phone = fields.Char(string='Contact Phone', related='unload_address.phone')
    unload_postcode = fields.Char(string='Postcode', related='unload_address.postcode')
    unload_city = fields.Char(string='City', related='unload_address.city')
    unload_country = fields.Many2one('res.country', 'Unload Country', related='unload_address.country')
    unload_country_code = fields.Char('Country Code', related='unload_country.code')
    unload_address_timeslot = fields.Char('Timeslot')

    @api.model
    def create(self, values):
        """
            生成订单号
        """
        times = fields.Date.today()
        values['billno'] = self.env['ir.sequence'].next_by_code('seq.delivery.order.line', times)
        delivery_request = super(DeliveryOrderLine, self).create(values)
        return delivery_request


class DeliveryOrderCmrLine(models.Model):
    _name = 'panexlogi.delivery.order.cmr.line'
    _description = 'panexlogi.delivery.order.cmr.line'
    _rec_name = 'billno'

    billno = fields.Char(string='BillNo', readonly=True)
    loading_ref = fields.Char(string='Loading Ref')
    cntrno = fields.Char('Container No')

    loading_conditon = fields.Many2one('panexlogi.loadingcondition', ' Condition')
    unloading_conditon = fields.Many2one('panexlogi.loadingcondition', 'Condition')
    planned_for_loading = fields.Datetime(string='Planned Loading')
    planned_for_unloading = fields.Datetime(string='Planned Unloading')
    product = fields.Many2one('product.product', 'Product')
    product_name = fields.Char('Product Name', related='product.name')
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
    adr = fields.Boolean(string='ADR')
    remark = fields.Text('Remark')
    cmr_file = fields.Binary(string='CMR File')
    cmr_filename = fields.Char(string='CMR File Name')
    cmr_signed = fields.Binary(string='CMR Signed')
    cmr_signed_filename = fields.Char(string='CMR Signed File Name')
    pod_file = fields.Binary(string='POD File')
    pod_filename = fields.Char(string='POD File Name')
    delivery_order_id = fields.Many2one('panexlogi.delivery.order', string='Delivery Order')

    @api.model
    def create(self, values):
        """
            生成订单号
        """
        times = fields.Date.today()
        values['billno'] = self.env['ir.sequence'].next_by_code('seq.delivery.order.cmr.line', times)
        delivery_request = super(DeliveryOrderCmrLine, self).create(values)
        return delivery_request
