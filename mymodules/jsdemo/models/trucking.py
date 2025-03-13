from odoo import models, fields, _, api


class Trucking(models.Model):
    _name = 'jsdemo.trucking'
    _description = 'Trucking Order Management'

    date = fields.Date(
        string='Date',
        readonly=True,
        default=fields.Date.context_today,
        help="Date when the trucking order was created"
    )
    project = fields.Char(
        string='Project',
        help="Reference to the project or client this order belongs to"
    )
    remark = fields.Text(
        'Remarks',
        help="Additional notes or comments about the trucking order"
    )
    price = fields.Float(
        'Total Price',
        help="Total price of the trucking order (auto-calculated)"
    )
    trucker = fields.Char(
        string='Trucker',
        help="Name of the truck driver or carrier company"
    )
    trucking_line_ids = fields.One2many(
        'jsdemo.trucking.line',
        'trucking_id',
        string='Items',
        help="List of products/items being transported"
    )

    def action_add_section(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'jsdemo.trucking.line',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_display_type': 'line_section',
                'default_parent_id': self.id
            }
        }

    def action_add_note(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'jsdemo.trucking.line',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_display_type': 'line_note',
                'default_parent_id': self.id
            }
        }

class TruckingLine(models.Model):
    _name = 'jsdemo.trucking.line'
    sequence = fields.Integer(default=10)
    display_type = fields.Selection(
        [('line_section', "Section"), ('line_note', "Note")],
        default=False,
        help="Technical field for UX purpose"
    )
    name = fields.Text(string="Description")
    product_id = fields.Many2one('product.product', string="Product")
    quantity = fields.Float()
    price = fields.Float()
    trucking_id = fields.Many2one(
        'jsdemo.trucking',
        string='Trucking Order',
        help="Reference to the main trucking order"
    )
    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id and self.product_id.detailed_type == 'service':
            self.update({
                'display_type': 'line_section' if self.product_id.sale_line_warn == 'section' else 'line_note',
                'quantity': 0,
                'price': 0
            })




    def paste_lines(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Paste Lines',
            'res_model': 'trucking.paste.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_trucking_id': self.id,
            }
        }

    @api.model
    def process_pasted_data(self, pasted_lines, trucking_id):
        Product = self.env['product.product']
        records = []

        for line in pasted_lines:
            cells = line.split('\t')
            if len(cells) >= 3:
                product_name = cells[0].strip()
                quantity = float(cells[1].strip()) if cells[1].strip() else 0.0
                price = float(cells[2].strip()) if cells[2].strip() else 0.0

                product = Product.search([('name', 'ilike', product_name)], limit=1)

                records.append({
                    'trucking_id': trucking_id,
                    'product_id': product.id,
                    'quantity': quantity,
                    'price': price,
                })

        if records:
            return self.create(records)
        return False

class TruckingPasteWizard(models.TransientModel):
    _name = 'jsdemo.trucking.paste.wizard'
    _description = 'Paste Trucking Lines Wizard'

    trucking_id = fields.Many2one('jsdemo.trucking', required=True)
    pasted_data = fields.Text('Pasted Data', required=True)

    def action_import(self):
        Product = self.env['product.product']
        lines = []

        for line in self.pasted_data.split('\n'):
            cells = line.strip().split('\t')
            if len(cells) >= 3:
                product_name = cells[0].strip()
                quantity = cells[1].strip() or '0'
                price = cells[2].strip() or '0'

                product = Product.search([('name', 'ilike', product_name)], limit=1)

                lines.append({
                    'trucking_id': self.trucking_id.id,
                    'product_id': product.id,
                    'quantity': float(quantity),
                    'price': float(price),
                })

        if lines:
            self.env['jsdemo.trucking.line'].create(lines)

        return {'type': 'ir.actions.act_window_close'}
