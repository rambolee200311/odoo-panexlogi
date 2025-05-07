from odoo import _, models, fields, api, exceptions, tools
from odoo.exceptions import UserError
import base64
from io import BytesIO
import openpyxl
from openpyxl.styles import Font
from openpyxl.styles import Alignment

'''
    Transport Order
'''


class TransportOrder(models.Model):
    _name = 'panexlogi.transport.order'
    _description = 'panexlogi.transport.order'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = 'billno'

    billno = fields.Char(string='BillNo', readonly=True)
    date = fields.Date(string='Date', default=fields.Date.today)
    issue_date = fields.Date(string='Order Date')
    project = fields.Many2one('panexlogi.project', string='Project', required=True)
    project_code = fields.Char(string='Project Code', related='project.project_code')
    waybill_billno = fields.Many2one('panexlogi.waybill', string='Waybill No inner')
    waybillno = fields.Char(string='Waybill No', related='waybill_billno.waybillno', readonly=True)

    truckco = fields.Many2one('res.partner', string='Truck Co（卡车公司）', domain=[('truck', '=', 'True')])
    truckco_code = fields.Char(string='Truck Co Code', related='truckco.panex_code', readonly=True)

    cargodesc = fields.Text(string='Cargo Description')

    collterminal = fields.Many2one('panexlogi.terminal', string='Collection Terminal')
    collterminal_code = fields.Char(string='Collection Terminal Code', related='collterminal.terminal_code',
                                    readonly=True)
    coldate = fields.Date(string='Collection Date')
    warehouse = fields.Many2one('stock.warehouse', string='Unloaded Warehouse')
    warehouse_code = fields.Char(string='Warehouse Code', related='warehouse.code', readonly=True)
    unlolocation = fields.Char(string='Unloaded Location')
    unlodate = fields.Date(string='Unloaded Date')

    dropterminal = fields.Many2one('panexlogi.terminal', string='Empty Container Drop-off Terminal')
    dropterminal_code = fields.Char(string='Drop-off Terminal Code', related='dropterminal.terminal_code',
                                    readonly=True)

    drop_off_planned_date = fields.Date(string='Drop-off Planned Date')

    special_instructions = fields.Text(string='Special Instructions')
    additional_comments = fields.Text(string='Additional Comments')

    remark = fields.Text(string='Remark')
    transportorderdetailids = fields.One2many('panexlogi.transport.order.detail', 'transportorderid',
                                              string='Container NO')
    transportorderotherdocs_ids = fields.One2many('panexlogi.transport.order.otherdocs', 'billno', string='Other Docs')

    state = fields.Selection(
        selection=[
            ('new', 'New'),
            ('confirm', 'Confirm'),
            ('received', 'Received'),
            ('cancel', 'Cancel'),
        ],
        default='new',
        string="Status",
        tracking=True
    )
    arrived_date = fields.Date(string='Arrived Date')
    adr = fields.Boolean(string='ADR')

    def action_confirm_order(self):
        for rec in self:
            if rec.state != 'new':
                raise UserError(_("You only can confirm New Order"))
            else:
                if not rec.issue_date:
                    raise UserError(_("Order Date is required!"))
                if not rec.truckco:
                    raise UserError(_("Truck Co is required!"))

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
    def create(self, values):
        """
        生成跟踪单号
        """
        times = fields.Date.today()
        values['billno'] = self.env['ir.sequence'].next_by_code('seq.transport.order', times)
        values['state'] = 'new'

        return super(TransportOrder, self).create(values)

    # 发邮件给卡车公司
    def action_send_email(self):
        template_id = self.env.ref('panexLogi.email_template_transport_order').id
        self.env['mail.template'].browse(template_id).send_mail(self.id, force_send=True)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': 'Email sent successfully!',
                'type': 'success',
                'sticky': False,
            }
        }

    # 生成入库单
    def action_create_inbound_order(self):
        # 生成入库订单
        owarehouse = 0
        iwarehouse = 0
        transport_order_details = []
        for record in self:
            for detail in record.transportorderdetailids:
                if owarehouse != detail.warehouse.id and detail.warehouse.id:
                    owarehouse = detail.warehouse.id
                    transport_order_detail = self.env['panexlogi.transport.order.detail'].search(
                        [('warehouse', '=', owarehouse)])
                    transport_order_details.append(transport_order_detail)
            for order_detail in transport_order_details:
                # inbound_order_product_ids

                detail_list = []
                for rec in order_detail:
                    # way bill pack list
                    packlist = self.env['panexlogi.waybill.packlist'].search(
                        [('cntrno', '=', rec.cntrno)])
                    for pack in packlist:
                        detail_list.append((0, 0, {
                            'cntrno': pack.cntrno,
                            'product_id': pack.product_id.id,
                            'batch': pack.batch,
                            'pcs': pack.pcs,
                            'pallets': pack.pallets,
                        }))
                    iwarehouse = rec.warehouse.id
                    # inbound_order
                order = {
                    'date': fields.Date.today(),
                    'project': record.project.id,
                    'warehouse': iwarehouse,
                    'inbound_order_product_ids': detail_list,
                }
                self.env['panexlogi.inbound.order'].create(order)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': 'Inbound Order create successfully!',
                'type': 'success',
                'sticky': False,
            }
        }

    # 生成CMR文件
    def generate_cmr_file(self):
        try:
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

            style = 'common_style'
            template_record = self.env['panexlogi.excel.template'].search([('type', '=', 'inbound')], limit=1)
            if self.project.project_code == 'HIH-trina':
                style = 'hih_style'
                template_record = self.env['panexlogi.excel.template'].search(
                    [('type', '=', 'inbound'), ('project', '=', 'HIH-trina')], limit=1)
            if not template_record:
                raise UserError(_('Template not found!'))
            template_data = base64.b64decode(template_record.template_file)
            template_buffer = BytesIO(template_data)
            for rec in self:
                shipping = rec.waybill_billno.shipping.name if rec.waybill_billno.shipping else ''
                # check teminal is not empty
                if not rec.collterminal:
                    raise UserError(_('Terminal is required!'))
                # check warehouse is not empty
                for detail in rec.transportorderdetailids:
                    if not detail.warehouse:
                        raise UserError(_('Warehouse is required!'))
                for detail in rec.transportorderdetailids:
                    # generate CMR file based details
                    bill_num = rec.waybill_billno.waybillno
                    cntrno = detail.cntrno
                    # pallets = detail.pallets
                    # model_type = detail.model_type
                    # weight_kg = detail.weight_kg
                    # receiver = rec.waybill_billno.project.customer.name
                    # teminal = rec.collterminal.terminal_name
                    # total_pcs = detail.total_pcs
                    # combinate teminal address with street,zip,city,country
                    teminal_address_parts = []
                    if rec.collterminal.address.street:
                        teminal_address_parts.append(rec.collterminal.address.street)
                    if rec.collterminal.address.zip:
                        teminal_address_parts.append(rec.collterminal.address.zip)
                    if rec.collterminal.address.city:
                        teminal_address_parts.append(rec.collterminal.address.city)
                    if rec.collterminal.address.country_id.name:
                        teminal_address_parts.append(rec.collterminal.address.country_id.name)
                    # 用逗号+空格分隔非空字段（例如：Street, 12345 City, State）
                    # teminal_full_address = ', '.join(teminal_address_parts) if teminal_address_parts else ''
                    teminal_name = rec.collterminal.address.name if rec.collterminal.address.name else ''
                    project_name = rec.project.project_name if rec.project else ''

                    warehouse_address_parts = []
                    if detail.warehouse.partner_id.street:
                        warehouse_address_parts.append(detail.warehouse.partner_id.street)
                    if detail.warehouse.partner_id.zip:
                        warehouse_address_parts.append(detail.warehouse.partner_id.zip)
                    if detail.warehouse.partner_id.city:
                        warehouse_address_parts.append(detail.warehouse.partner_id.city)
                    warehouse_full_address = ', '.join(warehouse_address_parts) if warehouse_address_parts else ''
                    warehouse_city_name = detail.warehouse.partner_id.city if detail.warehouse.partner_id.city else ''
                    warehouse_country_name = detail.warehouse.partner_id.country_id.name if detail.warehouse.partner_id.country_id else ''
                    warehouse_name = detail.warehouse.name if detail.warehouse.name else ''

                    shipping = detail.packlist_ids[0].shipping if detail.packlist_ids else ''

                    # Load the template workbook
                    workbook = openpyxl.load_workbook(template_buffer)

                    # hih_style(workbook)
                    def set_cell_style(cell, alignment, font):
                        cell.alignment = alignment
                        cell.font = font

                    def common_style(workbook):  # common style
                        worksheet = workbook.active
                        # Write data to the specified cells
                        worksheet['B6'] = ''
                        worksheet['B6'] = project_name
                        worksheet['B7'] = ''
                        worksheet['B7'] = teminal_name
                        worksheet['B13'] = ''
                        worksheet['B13'] = warehouse_full_address
                        worksheet['B20'] = ''
                        worksheet['B20'] = warehouse_city_name
                        worksheet['B21'] = ''
                        worksheet['B21'] = warehouse_country_name
                        worksheet['D21'] = ''
                        worksheet['D21'] = fields.Date.today().strftime('  -   -%Y  (DD-MM-YYYY)')  # --2025
                        worksheet['B27'] = ''
                        worksheet['B29'] = ''
                        worksheet['B29'] = bill_num

                        worksheet['J28'] = ''
                        worksheet['J28'] = 'Pieces'
                        cell = worksheet['J28']
                        cell.alignment = ALIGN_TOP_LEFT
                        cell.font = ARIAL_10
                        worksheet['D29'] = ''
                        worksheet['D29'] = cntrno

                        row = 29
                        total_pallets = 0
                        total_pcs = 0

                        worksheet['F29'] = ''
                        worksheet['H29'] = ''
                        worksheet['I29'] = ''
                        worksheet['J29'] = ''
                        if detail.packlist_ids:
                            for packlist in detail.packlist_ids:
                                if packlist.product_id:
                                    model = packlist.product_id.model or ''
                                    name = packlist.product_id.name or ''
                                    worksheet[f'F{row}'] = f'[{model}]{name}'
                                    set_cell_style(worksheet[f'F{row}'], ALIGN_TOP_LEFT, ARIAL_10)

                                gross_weight = packlist.gw or 0
                                if gross_weight == 0 and packlist.gwp:
                                    if packlist.pallets:
                                        gross_weight = packlist.gwp * packlist.pallets
                                    elif packlist.pcs:
                                        gross_weight = packlist.gwp * packlist.pcs

                                worksheet[f'H{row}'] = f'{packlist.pallets or 0}'
                                set_cell_style(worksheet[f'H{row}'], ALIGN_TOP_RIGHT, ARIAL_10)

                                worksheet[f'I{row}'] = f'{gross_weight}'
                                set_cell_style(worksheet[f'I{row}'], ALIGN_TOP_RIGHT, ARIAL_10)

                                worksheet[f'J{row}'] = f'{packlist.pcs or 0}'
                                set_cell_style(worksheet[f'J{row}'], ALIGN_TOP_RIGHT, ARIAL_10)

                                total_pallets += packlist.pallets or 0
                                total_pcs += packlist.pcs or 0
                                row += 1
                        else: # packlist_ids is empty
                            worksheet['F29'] = detail.model_type if detail.model_type else ''
                            set_cell_style(worksheet['F29'], ALIGN_TOP_LEFT, ARIAL_10)
                            worksheet['H29'] = f'{detail.pallets or 0}'
                            total_pallets += detail.pallets or 0
                            set_cell_style(worksheet['H29'], ALIGN_TOP_RIGHT, ARIAL_10)
                            worksheet['I29'] = f'{detail.weight_kg or 0}'
                            set_cell_style(worksheet['I29'], ALIGN_TOP_RIGHT, ARIAL_10)
                            worksheet['J29'] = f'{detail.total_pcs or 0}'
                            set_cell_style(worksheet['J29'], ALIGN_TOP_RIGHT, ARIAL_10)
                            total_pcs += detail.total_pcs or 0


                        worksheet['G36'] = 'Total Pallets:'
                        worksheet['H36'] = total_pallets
                        set_cell_style(worksheet['H36'], ALIGN_TOP_RIGHT, ARIAL_10)

                        worksheet['G37'] = 'Total Pieces:'
                        worksheet['H37'] = total_pcs
                        set_cell_style(worksheet['H37'], ALIGN_TOP_RIGHT, ARIAL_10)
                        worksheet['B48'] = ''
                        worksheet['B48'] = warehouse_name

                    def hih_style(workbook):  # hih style
                        worksheet = workbook.active
                        # Write data to the specified cells
                        worksheet['B6'] = ''
                        worksheet['B7'] = project_name
                        worksheet['B8'] = rec.collterminal.terminal_name if rec.collterminal.terminal_name else ''
                        worksheet['B9'] = rec.collterminal.zip if rec.collterminal.zip else ''
                        worksheet['B9'] = rec.collterminal.city if rec.collterminal.city else ''
                        worksheet['B16'] = warehouse_full_address
                        worksheet['B17'] = warehouse_city_name
                        worksheet['B18'] = warehouse_country_name
                        worksheet['D17'] = fields.Date.today().strftime('  -   -%Y  (DD-MM-YYYY)')  # --2025
                        worksheet['B25'] = shipping
                        worksheet['C25'] = bill_num
                        worksheet['G25'] = cntrno
                        row = 25
                        total_pallets = 0
                        total_pcs = 0

                        for packlist in detail.packlist_ids:
                            if packlist.product_id:
                                model = packlist.product_id.model or ''
                                name = packlist.product_id.name or ''
                                worksheet[f'F{row}'] = packlist.batch if packlist.batch else ''
                                set_cell_style(worksheet[f'F{row}'], ALIGN_TOP_LEFT, ARIAL_10)
                            """
                            gross_weight = packlist.gw or 0
                            if gross_weight == 0 and packlist.gwp:
                                if packlist.pallets:
                                    gross_weight = packlist.gwp * packlist.pallets
                                elif packlist.pcs:
                                    gross_weight = packlist.gwp * packlist.pcs
                            """

                            worksheet[f'H{row}'] = f'{packlist.pallets or 0}'
                            set_cell_style(worksheet[f'H{row}'], ALIGN_TOP_RIGHT, ARIAL_10)

                            worksheet[f'I{row}'] = f'{packlist.pcs or 0}'
                            set_cell_style(worksheet[f'I{row}'], ALIGN_TOP_RIGHT, ARIAL_10)

                            total_pallets += packlist.pallets or 0
                            total_pcs += packlist.pcs or 0
                            row += 1

                        worksheet['G41'] = 'Total Pallets:'
                        worksheet['H41'] = total_pallets
                        set_cell_style(worksheet['H41'], ALIGN_TOP_RIGHT, ARIAL_10)
                        """
                        worksheet['G37'] = 'Total Pieces:'
                        worksheet['H37'] = total_pcs
                        set_cell_style(worksheet['H37'], ALIGN_TOP_RIGHT, ARIAL_10)
                        """
                        worksheet['B43'] = ''
                        worksheet['B43'] = warehouse_name

                    # Save the workbook to a BytesIO object
                    if style == 'common_style':
                        common_style(workbook)
                    elif style == 'hih_style':
                        hih_style(workbook)

                    excel_buffer = BytesIO()
                    workbook.save(excel_buffer)
                    excel_buffer.seek(0)
                    detail.cmr_file = base64.b64encode(excel_buffer.read())
                    detail.cmr_filename = f'CMR_{rec.billno}_{cntrno}.xlsx'
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

    """
    @api.constrains('waybill_billno')
    def _check_waybillno_id(self):
        for r in self:
            domain = [
                ('waybill_billno', '=', r.waybill_billno.id),
                ('state', '!=', 'cancel'),
                ('id', '!=', r.id),
            ]
            existing_records = self.search(domain)
            if existing_records:
                raise UserError(_('waybill_billno must be unique per transport order!'))
    """

    # 维护到港实际日期 跳转wizard视图
    def add_actual_date(self):
        if not self.id:
            raise exceptions.ValidationError('Please save the record first.')
        if self.state != 'confirm':
            raise exceptions.ValidationError('Only confirmed orders can be modified to arrival.')
        return {
            'name': 'Actual Arrival Date',
            'type': 'ir.actions.act_window',
            'res_model': 'panexlogi.transport.order.arrived.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_billno': self.id},
        }

    # batch edit
    def open_batch_edit_wizard(self):
        for rec in self:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Batch Edit Container Details',
                'res_model': 'panexlogi.transport.order.detail.batch.edit.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_transportorderid': rec.id,
                    'default_detail_ids': rec.transportorderdetailids.ids,
                }
            }

    @staticmethod
    def format_multi_line(values):
        """Process multiple values into a multi-line string."""
        return '\n'.join(str(v) for v in values) if values else ''


class TransportOrderDetail(models.Model):
    _name = 'panexlogi.transport.order.detail'
    _description = 'panexlogi.transport.order.detail'
    _inherit = ["mail.thread", "mail.activity.mixin"]

    cntrno = fields.Char(string='Container NO')
    pallets = fields.Float(string='Pallets', default=26)
    uncode = fields.Char('UN CODE')
    coldate = fields.Date(string='Collection Date')
    warehouse = fields.Many2one('stock.warehouse', string='Unloaded Warehouse')
    warehouse_code = fields.Char(string='Warehouse Code', related='warehouse.code', readonly=True)
    unlolocation = fields.Char(string='Unloaded Location')
    unlodate = fields.Date(string='Unloaded Date')
    dropterminal = fields.Many2one('panexlogi.terminal', string='Empty Container Drop-off Terminal')
    dropterminal_code = fields.Char(string='Drop-off Terminal Code', related='dropterminal.terminal_code',
                                    readonly=True)
    drop_off_planned_date = fields.Date(string='Drop-off Planned Date')
    special_instructions = fields.Text(string='Special Instructions')
    additional_comments = fields.Text(string='Additional Comments')
    remark = fields.Text(string='Remark')

    transportorderid = fields.Many2one('panexlogi.transport.order', string='Transport Order')

    state = fields.Selection(selection=[
        ('new', 'New'),
        ('arrived', 'Arrived'),
    ],
        default='new',
        string="Status",
        tracking=True
    )
    arrived_date = fields.Date(string='Arrived Date')
    cmr_file = fields.Binary(string='CMR File')
    cmr_filename = fields.Char(string='CMR File name')

    waybill_detail_id = fields.Many2one('panexlogi.waybill.details', string='Waybill Detail ID')
    # In the panexlogi.transport.order.detail model

    packlist_ids = fields.One2many(
        'panexlogi.waybill.packlist',
        related='waybill_detail_id.waybill_packlist_id',
        string='Packing Lists',
        readonly=True
    )


# 其他附件
class TransportOrderOtherDocs(models.Model):
    _name = 'panexlogi.transport.order.otherdocs'
    _description = 'panexlogi.transport.order.otherdocs'

    description = fields.Text(string='Description')
    file = fields.Binary(string='File')
    filename = fields.Char(string='File name')
    billno = fields.Many2one('panexlogi.transport.order', string='Transport Order BillNo')


class TransportOrderArrivedWizard(models.TransientModel):
    _name = 'panexlogi.transport.order.arrived.wizard'
    _description = 'panexlogi.transport.order.arrived.wizard'

    arrived_date = fields.Date(string='Arrived Date', default=fields.Date.today)
    billno = fields.Many2one('panexlogi.transport.order', string='Transport Order', required=True)
    cntrnos = fields.Many2many('panexlogi.transport.order.cntrnos'
                               , string='Container NOs'
                               , relation='transport_order_arrived_cntro_rel'
                               , domain="[('transport_order_id', '=', billno)]")
    cmr_file = fields.Binary(string='CMR File')
    cmr_filename = fields.Char(string='CMR File name')
    """
    @api.onchange('billno')
    def _onchange_billno(self):
        if self.billno.billno:
            return {'domain': {'cntrnos': [('billno', '=', self.billno.billno)]}}
        else:
            return {'domain': {'cntrnos': []}}
    """

    def apply_changes(self):
        for cntrno in self.cntrnos:
            detail = self.billno.transportorderdetailids.filtered(lambda x: x.cntrno == cntrno.cntrno)
            detail.state = 'arrived'  # Example operation: update state to 'arrived'
            detail.arrived_date = self.arrived_date
            detail.cmr_file = self.cmr_file
            detail.cmr_filename = self.cmr_filename
        return {'type': 'ir.actions.act_window_close'}


class TransportOrderCntrnos(models.Model):
    _name = 'panexlogi.transport.order.cntrnos'
    _description = 'Transport Order Cntrno Report'
    _auto = False
    _rec_name = 'cntrno'

    cntrno = fields.Char(string='Container NO')
    transport_order_id = fields.Integer(string='Transport Order ID')
    billno = fields.Char(string='BillNo')

    @api.model
    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)
        self._cr.execute("""
                CREATE OR REPLACE VIEW panexlogi_transport_order_cntrnos AS (
                    SELECT
                        row_number() OVER () AS id,
                        d.cntrno AS cntrno,
                        o.id as transport_order_id,
                        o.billno as billno
                    FROM
                    panexlogi_transport_order o
                    join panexlogi_transport_order_detail d on o.id = d.transportorderid
                    where o.state = 'confirm'   )
        """)


class TransportOrderDetailBatchEditWizard(models.TransientModel):
    _name = 'panexlogi.transport.order.detail.batch.edit.wizard'
    _description = 'Batch Edit Transport Order Details'

    transportorderid = fields.Many2one('panexlogi.transport.order', string='Transport Order')
    detail_ids = fields.Many2many(
        'panexlogi.transport.order.detail',
        string='Container Details',
        domain="[('transportorderid', '=', transportorderid)]",
        relation='transportorder_batch_edit_details_rel'  # Shorter table name
    )

    coldate = fields.Date(string='Collection Date')
    warehouse = fields.Many2one('stock.warehouse', string='Unloaded Warehouse')
    unlolocation = fields.Char(string='Unloaded Location')
    unlodate = fields.Date(string='Unloaded Date')
    dropterminal = fields.Many2one('panexlogi.terminal', string='Drop-off Terminal')
    drop_off_planned_date = fields.Date(string='Drop-off Date')
    model_type = fields.Char(string='Model Type')
    weight_kg = fields.Float(string='Weight (kg)')
    total_pcs = fields.Float(string='Total Pieces')

    def apply_changes(self):
        for rec in self:
            for detail in rec.detail_ids:
                if rec.coldate:
                    detail.coldate = rec.coldate
                if rec.warehouse:
                    detail.warehouse = rec.warehouse
                if rec.unlolocation:
                    detail.unlolocation = rec.unlolocation
                if rec.dropterminal:
                    detail.dropterminal = rec.dropterminal
                if rec.drop_off_planned_date:
                    detail.drop_off_planned_date = rec.drop_off_planned_date
                if rec.model_type:
                    detail.model_type = rec.model_type
                if rec.weight_kg:
                    detail.weight_kg = rec.weight_kg
                if rec.total_pcs:
                    detail.total_pcs = rec.total_pcs
                if rec.unlodate:
                    detail.unlodate = rec.unlodate
        return {'type': 'ir.actions.act_window_close'}
