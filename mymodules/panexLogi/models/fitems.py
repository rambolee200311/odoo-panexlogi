import calendar

from odoo import _, models, fields, api, exceptions
from odoo.exceptions import UserError


# 收入成本费用项目

class Fitems(models.Model):
    _name = 'panexlogi.fitems'
    _description = 'panexlogi.fitems'
    _rec_name = 'code'

    code = fields.Char(string='项目编码', required=True)
    name = fields.Char(string='项目名称', required=True)
    remark = fields.Text(string='Remark')
    remark1 = fields.Text(string='Remark1')
    booking_code = fields.Char(string='Booking Code(finance use only)')

    be_outcome = fields.Boolean("Outlay(费用支出)", default=True)
    be_income = fields.Boolean("Income（收入）", default=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirm'),
        ('cancel', 'Cancel'),
    ], string='Status', readonly=True, copy=False, index=True, default='draft')

    @api.constrains('code')
    def _check_code_id(self):
        for r in self:
            domain = [
                ('code', '=', r.code),
                ('id', '!=', r.id),
            ]
            existing_records = self.search(domain)
            if existing_records:
                raise UserError(_('Code must be unique per Finance item'))


# settle period
class Period(models.Model):
    _name = 'panexlogi.periods'
    _description = 'Accounting Periods'
    _rec_name = 'code'
    _order = 'year desc, month asc'

    year = fields.Integer(string="Year", required=True)
    month = fields.Integer(string="Month", required=True)
    month_name = fields.Char(string="Month Name", required=True)
    code = fields.Char(string="Code", required=True)

    def generate_periods(self):
        return {
            'name': 'Generate Accounting Periods',
            'type': 'ir.actions.act_window',
            'res_model': 'panexlogi.period.generate.wizard',
            'view_mode': 'form',
            'target': 'new',
        }

    def cron_generate(self):
        # 获取当前年份
        year = fields.Date.today().year

        # 检查是否存在记录
        existing = self.env['panexlogi.periods'].search_count([('year', '=', year)])
        if not existing:
            # 创建期间记录
            periods = []
            for month in range(1, 13):
                periods.append({
                    'year': year,
                    'month': month,
                    'month_name': calendar.month_abbr[month].upper(),
                    'code': f"{year}-{month:02d}"
                })

            self.env['panexlogi.periods'].create(periods)




class PeriodGenerateWizard(models.TransientModel):
    _name = 'panexlogi.period.generate.wizard'
    _description = 'Generate Accounting Periods Wizard'

    year = fields.Integer(
        string='Year',
        required=True,
        default=lambda self: fields.Date.today().year
    )

    def action_generate(self):
        #self.ensure_one()

        # 输入验证
        if self.year < 1970 or self.year > 2100:
            raise UserError(_("year must be between 1970 and 2100"))

        # 检查是否存在记录
        existing = self.env['panexlogi.periods'].search_count([('year', '=', self.year)])
        if existing:
            raise UserError(_("%year is existed") % self.year)

        # 创建期间记录
        periods = []
        for month in range(1, 13):
            periods.append({
                'year': self.year,
                'month': month,
                'month_name': calendar.month_abbr[month].upper(),
                'code': f"{self.year}-{month:02d}"
            })

        self.env['panexlogi.periods'].create(periods)

        # 关闭向导并刷新视图
        return {
            'type': 'ir.actions.act_window_close',
            'infos': {'period_generated': True}
        }
