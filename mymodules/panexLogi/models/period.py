from datetime import datetime, timedelta
from odoo import fields, models, api
import logging

_logger = logging.getLogger(__name__)

class FiscalYear(models.Model):
    _name = 'fiscal.year'
    _description = 'Fiscal Year'

    name = fields.Char(string="Year", required=True)
    start_date = fields.Date(string="Start Date")
    end_date = fields.Date(string="End Date")
    quarter_ids = fields.One2many('fiscal.quarter', 'year_id', string="Quarters")

    @api.model
    def create(self, values):
        # Ensure the name field is provided
        if 'name' not in values or not values['name']:
            raise ValueError("The 'name' field is required.")

        try:
            # Convert the name to an integer to validate the year
            year_value = int(values['name'])
            # Calculate start_date and end_date
            values['start_date'] = datetime(year_value, 1, 1).strftime('%Y-%m-%d')
            values['end_date'] = datetime(year_value, 12, 31).strftime('%Y-%m-%d')
        except ValueError:
            raise ValueError("Invalid year format. Please enter a valid year.")

        # Create the fiscal year record
        fiscal_year = super(FiscalYear, self).create(values)

        # Automatically create quarters and months
        fiscal_year.create_quarters()
        fiscal_year.generate_months()

        return fiscal_year

    def create_quarters(self):
        for year in self:
            quarters = [
                ('Q1', '01-01', '03-31'),
                ('Q2', '04-01', '06-30'),
                ('Q3', '07-01', '09-30'),
                ('Q4', '10-01', '12-31')
            ]
            for name, start_suffix, end_suffix in quarters:
                start_date = f"{year.start_date.year}-{start_suffix}"
                end_date = f"{year.start_date.year}-{end_suffix}"
                if not self.env['fiscal.quarter'].search([('name', '=', name), ('year_id', '=', year.id)]):
                    self.env['fiscal.quarter'].create({
                        'name': name,
                        'start_date': start_date,
                        'end_date': end_date,
                        'year_id': year.id
                    })

    def generate_months(self):
        try:
            for year in self:
                # create a mapping for month names and codes
                months = [
                    ('JAN', '01'), ('FEB', '02'), ('MAR', '03'),
                    ('APR', '04'), ('MAY', '05'), ('JUN', '06'),
                    ('JUL', '07'), ('AUG', '08'), ('SEP', '09'),
                    ('OCT', '10'), ('NOV', '11'), ('DEC', '12')
                ]
                # get year value from name
                year_value = int(year.name)
                # create a mapping for quarters
                quarter_map = {
                    '01': 'Q1', '02': 'Q1', '03': 'Q1',
                    '04': 'Q2', '05': 'Q2', '06': 'Q2',
                    '07': 'Q3', '08': 'Q3', '09': 'Q3',
                    '10': 'Q4', '11': 'Q4', '12': 'Q4'
                }
                # create months
                for name, code in months:
                    month_start = datetime(year_value, int(code), 1)
                    # calculate the end date of the month,considering leap years
                    if code == '02' and self._is_leap_year(year_value):
                        month_end = datetime(year_value, 2, 29)
                    else:
                        next_month = month_start.replace(day=28) + timedelta(days=4)
                        month_end = next_month - timedelta(days=next_month.day)
                    # get the quarter based on the month code
                    quarter = self.env['fiscal.quarter'].search([
                        ('year_id', '=', year.id),
                        ('name', '=', quarter_map[code])
                    ], limit=1)
                    if not self.env['fiscal.month'].search([('name', '=', name), ('year_id', '=', year.id)]):
                        self.env['fiscal.month'].create({
                            'name': name,
                            'code': code,
                            'start_date': month_start.strftime('%Y-%m-%d'),
                            'end_date': month_end.strftime('%Y-%m-%d'),
                            'year_id': year.id,
                            'quarter_id': quarter.id
                        })
        except Exception as e:
            _logger.error(f"Error generating months: {e}")

    def _is_leap_year(self, year_value):
        """判断是否为闰年"""
        year = int(year_value)
        return (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)


class FiscalMonth(models.Model):
    _name = 'fiscal.month'
    _description = 'Fiscal Month'

    name = fields.Char(string="Month", required=True)
    code = fields.Char(string="Code", required=True)
    start_date = fields.Date(string="Start Date", required=True)
    end_date = fields.Date(string="End Date", required=True)
    year_id = fields.Many2one('fiscal.year', string="Year", required=True, ondelete='cascade')
    quarter_id = fields.Many2one('fiscal.quarter', string="Quarter", ondelete='cascade')


class FiscalQuarter(models.Model):
    _name = 'fiscal.quarter'
    _description = 'Fiscal Quarter'

    name = fields.Char(string="Quarter", required=True)
    start_date = fields.Date(string="Start Date", required=True)
    end_date = fields.Date(string="End Date", required=True)
    year_id = fields.Many2one('fiscal.year', string="Year", required=True, ondelete='cascade')
    month_ids = fields.One2many('fiscal.month', 'quarter_id', string="Months")