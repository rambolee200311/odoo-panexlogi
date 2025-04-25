from odoo import models, api
from datetime import datetime, timedelta

class IrSequence(models.Model):
    _inherit = 'ir.sequence'

    @api.model
    def create_monthly_date_ranges(self):
        """Ensure date ranges are created for all sequences with use_date_range enabled."""
        today = datetime.today()
        start_date = today.replace(day=1)
        end_date = (start_date + timedelta(days=32)).replace(day=1) - timedelta(days=1)

        # Find all sequences with use_date_range enabled
        sequences = self.search([('use_date_range', '=', True)])
        for sequence in sequences:
            # Check if a date range already exists for this month
            existing_range = self.env['ir.sequence.date_range'].search([
                ('sequence_id', '=', sequence.id),
                ('date_from', '=', start_date),
                ('date_to', '=', end_date)
            ])
            if not existing_range:
                # Create a new date range
                self.env['ir.sequence.date_range'].create({
                    'sequence_id': sequence.id,
                    'date_from': start_date,
                    'date_to': end_date,
                    'number_next': 1,  # Reset to 1 for the new month
                })