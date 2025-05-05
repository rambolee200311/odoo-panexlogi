from odoo import models, api
from datetime import datetime
from dateutil.relativedelta import relativedelta

class IrSequence(models.Model):
    _inherit = 'ir.sequence'

    @api.model
    def create_monthly_date_ranges(self):
        """Generate monthly date ranges with strict date boundaries"""
        current_date = datetime.now().date()
        start_date = current_date.replace(day=1)  # 1st of the current month
        end_date = (start_date + relativedelta(months=1)) - relativedelta(days=1)  # Last day of the month

        # Corrected domain format
        sequences = self.env['ir.sequence'].search([('prefix', 'ilike', '%(year)s%(month)s%(day)s')])

        for seq in sequences:
            seq.use_date_range = True

        sequences = self.env['ir.sequence'].search([('use_date_range', '=', True)])  # Fetch all sequences with date ranges

        for seq in sequences:
            existing = self.env['ir.sequence.date_range'].search([
                ('sequence_id', '=', seq.id),
                ('date_from', '=', start_date),
                ('date_to', '=', end_date)
            ], limit=1)

            if not existing:
                self.env['ir.sequence.date_range'].create({
                    'sequence_id': seq.id,
                    'date_from': start_date,
                    'date_to': end_date,
                    'number_next_actual': 1  # Reset to 1
                })

    @api.model
    def create_date_ranges_for_period(self):
        """Create ir.sequence.date_range records from a specific start to end period."""
        start_date = datetime(2025, 5, 1)
        end_date = datetime(2035, 12, 31)
        sequences = self.env['ir.sequence'].search([('use_date_range', '=', True)])

        while start_date <= end_date:
            for seq in sequences:
                # Calculate the end of the current month
                month_end_date = (start_date + relativedelta(months=1)) - relativedelta(days=1)

                # Check if the date range already exists
                existing = self.env['ir.sequence.date_range'].search([
                    ('sequence_id', '=', seq.id),
                    ('date_from', '=', start_date.date()),
                    ('date_to', '=', month_end_date.date())
                ], limit=1)

                if not existing:
                    # Create the date range
                    self.env['ir.sequence.date_range'].create({
                        'sequence_id': seq.id,
                        'date_from': start_date.date(),
                        'date_to': month_end_date.date(),
                        'number_next_actual': 1  # Reset to 1
                    })

            # Move to the next month
            start_date += relativedelta(months=1)