import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class InboundOrder(models.Model):
    _name = 'world.depot.inbound.order'
    _description = 'world.depot.inbound.order'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = 'billno'

    billno = fields.Char(string='BillNo', readonly=True)
    date = fields.Date(string='Order Date', required=True, tracking=True, default=fields.Date.today)
    a_date = fields.Date(string='Arrival Date', required=False, tracking=True)
    owner = fields.Many2one('res.partner', string='Owner', required=True, tracking=True)
    project = fields.Many2one('project.project', string='Project', required=True)
    warehouse = fields.Many2one(comodel_name='stock.warehouse', string='Warehouse')
    remark = fields.Text(string='Remark')
    reference = fields.Char(string='Reference', required=False)
    bl_no = fields.Char(string='Bill of Lading', required=False)
    cntr_no = fields.Char(string='Container No', required=False)
    pallets = fields.Float(string='Pallets', required=False)

    state = fields.Selection(
        selection=[
            ('new', 'New'),
            ('confirm', 'Confirm'),
            ('cancel', 'Cancel')
        ],
        default='new',
        string="State",
        tracking=True
    )
    inbound_order_product_ids = fields.One2many(
        comodel_name='world.depot.inbound.order.product',
        inverse_name='inbound_order_id',
        string='Inbound Order Products'
    )
    stock_picking_id = fields.Many2one('stock.picking', string='Stock Picking', readonly=True,
                                       help='Reference to the related Stock Picking')

    @api.model
    def create(self, values):
        """
        generate bill number
        """
        times = fields.Date.today()
        values['billno'] = self.env['ir.sequence'].next_by_code('seq.inbound.order', times)
        return super(InboundOrder, self).create(values)

    def action_confirm(self):
        for record in self:
            if record.state == 'new':
                # Update state
                record.state = 'confirm'
            else:
                raise UserError(_("Only new orders can be confirmed."))

    def action_cancel(self):
        for record in self:
            if record.state == 'new':
                record.state = 'cancel'
            else:
                raise UserError(_("Only new orders can be cancelled."))

    def action_unconfirm(self):
        for record in self:
            if record.state == 'confirm':
                related_picking = self.env['stock.picking'].search(
                    [('inbound_order_id', '=', record.id), ('state', '=', 'done')], limit=1)
                if related_picking:
                    raise UserError(_("Cannot unconfirm an order with completed stock picking."))
                # Delete related receipts and stock moves not in "done" state
                related_receipts = self.env['stock.picking'].search([
                    ('inbound_order_id', '=', record.id),
                    ('state', '!=', 'done')
                ])
                for receipt in related_receipts:
                    related_moves = self.env['stock.move'].search([('picking_id', '=', receipt.id)])
                    related_moves.unlink()
                related_receipts.unlink()

                # Update state
                record.state = 'new'
            else:
                raise UserError(_("Only confirmed orders can be unconfirmed."))

    def action_create_stock_picking(self):
        """
        Action to create the related stock picking

        """

        for record in self:
            pakage_name = []
            if not record.bl_no:
                raise UserError(_("Bill of Lading number is required to create a stock picking."))
            else:
                pakage_name.append(record.bl_no)
            if not record.cntr_no:
                raise UserError(_("Container number is required to create a stock picking."))
            else:
                pakage_name.append(record.cntr_no)
            if not record.warehouse:
                raise UserError(_("Warehouse is required to create a stock picking."))

            # create a stock package
            pakage_name_str = '- '.join(pakage_name)
            package_exist = self.env['stock.quant.package'].search([('name', '=', pakage_name_str)], limit=1)
            if not package_exist:
                self.env['stock.quant.package'].create({
                    'name': pakage_name_str,
                    'package_use': 'disposable'
                })

            if record.state != 'confirm':
                raise UserError(_("Stock picking can only be created from confirmed orders."))
            # Check if stock picking already exists
            existing_picking = self.env['stock.picking'].search([('inbound_order_id', '=', record.id)], limit=1)
            if existing_picking:
                raise UserError(_("A stock picking already exists for this Inbound Order."))

            # Create stock picking
            picking_type = self.env['stock.picking.type'].search([
                ('code', '=', 'incoming'),
                ('warehouse_id', '=', record.warehouse.id)
            ], limit=1)
            if not picking_type:
                raise UserError(_("No incoming picking type found for the selected warehouse."))

            vendor_location = self.env['stock.location'].search([('usage', '=', 'supplier')], limit=1)
            picking = self.env['stock.picking'].create({
                'picking_type_id': picking_type.id,
                'location_id': picking_type.default_location_src_id.id if picking_type.default_location_src_id else vendor_location.id,
                'location_dest_id': picking_type.default_location_dest_id.id,
                'origin': record.billno,
                'partner_id': record.owner.id,
                'inbound_order_id': record.id,
            })

            # Create stock moves
            for product in record.inbound_order_product_ids:
                self.env['stock.move'].create({
                    'name': product.product_id.name,
                    'product_id': product.product_id.id,
                    'product_uom_qty': product.quantity,
                    'product_uom': product.product_id.uom_id.id,
                    'picking_id': picking.id,
                    'location_id': picking.location_id.id,
                    'location_dest_id': picking.location_dest_id.id,
                })
            # Update the stock picking reference in the inbound order
            record.picking_PICK = picking.id
            # Confirm the picking
            # picking.action_confirm()
            # return a success message
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Stock Picking Created'),
                    'message': _('Stock picking has been created successfully.'),
                    'sticky': False,
                }
            }

    def action_view_stock_picking(self):
        """
        Action to view the related stock picking
        """
        self.ensure_one()
        action = self.env.ref('stock.action_picking_tree_all').read()[0]
        action['domain'] = [('inbound_order_id', '=', self.id)]
        action['context'] = {'create': False}
        return action


class InboundOrderProduct(models.Model):
    _name = 'world.depot.inbound.order.product'
    _description = 'Inbound Order Product'

    inbound_order_id = fields.Many2one('world.depot.inbound.order', string='Inbound Order', required=True)
    cntr_no = fields.Char(string='Container No', required=False)
    pallets = fields.Float(string='Pallets', required=False)
    product_id = fields.Many2one('product.product', string='Product', required=True)
    quantity = fields.Float(string='Quantity', required=True)
    remark = fields.Text(string='Remark')
    is_serial_tracked = fields.Boolean(string='Tracked by Serial', compute='_compute_is_serial_tracked', store=True)

    @api.depends('product_id')
    def _compute_is_serial_tracked(self):
        for record in self:
            record.is_serial_tracked = record.product_id.tracking == 'serial'


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    inbound_order_id = fields.Many2one(
        comodel_name='world.depot.inbound.order',
        string='Inbound Order',
        help='Reference to the related Inbound Order',
        readonly=True
    )
    outbound_order_id = fields.Many2one(
        comodel_name='world.depot.outbound.order',
        string='Outbound Order',
        help='Reference to the related Outbound Order',
        readonly=True
    )
