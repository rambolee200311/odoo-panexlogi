from openpyxl.styles import Font
from openpyxl.styles import Alignment
from odoo import _, models, fields, api
from odoo.exceptions import UserError
import logging
import base64
from io import BytesIO
import openpyxl

_logger = logging.getLogger(__name__)


# Delivery CMR file
class DeliveryDatailCmr(models.Model):
    _name = 'panexlogi.delivery.detail.cmr'
    _description = 'panexlogi.delivery.detail.cmr'
    _rec_name = 'billno'

    billno = fields.Char(string='BillNo', readonly=True)
    delivery_detail_id = fields.Many2one('panexlogi.delivery.detail', string='Delivery Detail ID')
    trailer_type = fields.Many2one('panexlogi.trailertype', string='Type of trailer')
    loading_refs = fields.Char(string='Loading Refs')
    load_date = fields.Datetime(string='Loading Date')
    load_timeslot = fields.Char('Load Timeslot')
    load_company = fields.Char(string='Loading Company')
    consignee_refs = fields.Char(string='Consignee Refs')
    unload_date = fields.Datetime(string='Unloading Date')
    unload_timeslot = fields.Char('Unload Timeslot')
    unload_company = fields.Char(string='Unloading Company')
    cntrnos = fields.Char(string='Container Numbers')
    cmr_file = fields.Binary(string='CMR File')
    cmr_filename = fields.Char(string='CMR File name')
    cmr_remark = fields.Text(string='CMR Remark')
    delivery_id = fields.Many2one('panexlogi.delivery', string='Delivery ID')
    delivery_detail_ids = fields.One2many('panexlogi.delivery.detail', 'delivery_detail_cmr_id',
                                          string='Delivery Detail IDs')
    state = fields.Selection(
        selection=[('new', 'New'), ('confirm', 'Confirm'),
                   ('cancel', 'Cancel'),
                   ('order', 'Order Placed'),
                   ('transit', 'In Transit'),
                   ('delivery', 'Delivered'),
                   ('cancel', 'Cancel'),
                   ('return', 'Return'),
                   ('other', 'Other'),
                   ('complete', 'Complete'),
                   ], default='new',
        string="State", tracking=True)

    delivery_order_new_id = fields.Many2one('panexlogi.delivery.order.new', string='Delivery Order')

    outside_eu = fields.Boolean(string='Outside of EU')
    import_file = fields.Binary(string='Import File')
    import_filename = fields.Char(string='Import File Name')
    export_file = fields.Binary(string='Export File')
    export_filename = fields.Char(string='Export File Name')
    load_address = fields.Many2one('panexlogi.address', 'Load Address')
    unload_address = fields.Many2one('panexlogi.address', 'Unload Address')

    quote = fields.Float('Quote', default=0, compute='_compute_quote')  # 报价
    additional_cost = fields.Float('Additional Cost', default=0, compute='_compute_quote')  # 额外费用
    extra_cost = fields.Float('Extra Cost', default=0, compute='_compute_quote')  # 额外费用

    # Properly define company_id and exclude from tracking
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        tracking=False  # Explicitly disable tracking
    )

    @api.depends('delivery_detail_ids.quote', 'delivery_detail_ids.additional_cost', 'delivery_detail_ids.extra_cost')
    def _compute_quote(self):
        for r in self:
            r.quote = sum(detail.quote for detail in r.delivery_detail_ids)
            r.additional_cost = sum(detail.additional_cost for detail in r.delivery_detail_ids)
            r.extra_cost = sum(detail.extra_cost for detail in r.delivery_detail_ids)

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

            # check detail_ids if combination of load_address and unload_address is same
            load_address = self.detail_ids[0].load_address
            unload_address = self.detail_ids[0].unload_address
            for detail in self.detail_ids:
                if detail.load_address != load_address or detail.unload_address != unload_address:
                    raise UserError(_("Please select details with the same load and unload addresses."))

            load_address = []
            if self.detail_ids[0].load_address.company_name:
                load_address.append(self.detail_ids[0].load_address.company_name)
            if self.detail_ids[0].load_address.street:
                load_address.append(self.detail_ids[0].load_address.street)
            if self.detail_ids[0].load_address.postcode:
                load_address.append(self.detail_ids[0].load_address.postcode)
            if self.detail_ids[0].load_address.city:
                load_address.append(self.detail_ids[0].load_address.city)
            if self.detail_ids[0].load_address.country:
                load_address.append(self.detail_ids[0].load_address.country.name)

            unload_address = []
            if self.detail_ids[0].unload_address.company_name:
                unload_address.append(self.detail_ids[0].unload_address.company_name)
            if self.detail_ids[0].unload_address.street:
                unload_address.append(self.detail_ids[0].unload_address.street)
            if self.detail_ids[0].unload_address.postcode:
                unload_address.append(self.detail_ids[0].unload_address.postcode)
            if self.detail_ids[0].unload_address.city:
                unload_address.append(self.detail_ids[0].unload_address.city)
            if self.detail_ids[0].unload_address.country:
                unload_address.append(self.detail_ids[0].unload_address.country.name)

            worksheet['B6'] = ''
            worksheet['B6'] = self.delivery_id.project.project_name

            worksheet['B7'] = ''
            worksheet['B7'] = ', '.join(load_address)

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
            # cntrnos = [
            #    str(detail.cntrno) if detail.cntrno and str(detail.cntrno).lower() != 'false'
            #    else ''
            #    for detail in self.detail_ids
            # ]
            # load_refs = [
            #        str(detail.loading_ref) if detail.loading_ref and str(detail.loading_ref).lower() != 'false'
            #        else ''
            #        for detail in self.detail_ids
            # ]
            cntrnos_load_refs = [
                f"-{str(detail.loading_ref)}" if not detail.cntrno and detail.loading_ref and str(
                    detail.loading_ref).lower() != 'false'
                else f"{str(detail.cntrno)}-" if not detail.loading_ref and detail.cntrno and str(
                    detail.cntrno).lower() != 'false'
                else f"{str(detail.cntrno)}-{str(detail.loading_ref)}" if detail.cntrno and detail.loading_ref and str(
                    detail.cntrno).lower() != 'false' and str(detail.loading_ref).lower() != 'false'
                else ''
                for detail in self.detail_ids
            ]
            worksheet['D29'] = ''
            worksheet['D29'] = '\n'.join(cntrnos_load_refs)
            cell = worksheet['D29']
            cell.alignment = ALIGN_TOP_LEFT
            cell.font = ARIAL_10

            # Fix 3: Convert model types
            # model_types = [
            #    str(detail.model_type) if detail.model_type and str(detail.model_type).lower() != 'false'
            #    else ''
            #    for detail in self.detail_ids
            # ]
            model_types = [
                str(detail.model_type) if not detail.product and detail.model_type and str(
                    detail.model_type).lower() != 'false'
                else detail.product.name if detail.product and (
                        not detail.model_type or str(detail.model_type).lower() == 'false')
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
                # 'load_date': min(
                #    date for date in self.detail_ids.mapped('load_date') if date) if self.detail_ids.mapped(
                #    'load_date') else False,
                'load_date': min(
                    [date for date in self.detail_ids.mapped('load_date') if date]
                ) if any(self.detail_ids.mapped('load_date')) else False,
                'consignee_refs': ', '.join(str(ref) for ref in set(self.detail_ids.mapped('consignee_ref')) if ref),
                # ', '.join(set(ref for ref in self.detail_ids.mapped('consignee_ref') if ref)),
                # 'unload_date': min(
                #    date for date in self.detail_ids.mapped('unload_date') if date) if self.detail_ids.mapped(
                #    'unload_date') else False,
                'unload_date': min(
                    [date for date in self.detail_ids.mapped('unload_date') if date]
                ) if any(self.detail_ids.mapped('unload_date')) else False,
                'cntrnos': ', '.join(str(cntr) for cntr in set(self.detail_ids.mapped('cntrno')) if cntr),
                # ', '.join(set(cntr for cntr in self.detail_ids.mapped('cntrno') if cntr)),
                'cmr_file': base64.b64encode(excel_buffer.getvalue()),
                # 'cmr_filename': f'CMR_{self.delivery_id.billno}.xlsx',
                'cmr_remark': self.cmr_remark,
                'load_address': self.detail_ids[0].load_address.id,
                'unload_address': self.detail_ids[0].unload_address.id,
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
