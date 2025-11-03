from odoo import models, fields, api
from datetime import timedelta
from odoo.exceptions import UserError


class LunchWeekPlan(models.Model):
    _name = 'panexlogi.lunch.week.plan'
    _description = 'Employee Lunch Weekly Plan'

    name = fields.Char(
        string='Plan Reference',
        default="New",
        readonly=True
    )
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        default=lambda self: self.env.user.employee_id
    )
    week_date = fields.Date(
        string='Target Week',
        required=True,
        help="Select any day of the target week. The system will calculate the week automatically."
    )
    plan_week = fields.Integer(
        string='Week Number',
        compute='_compute_plan_week',
        store=True
    )
    plan_week_begin = fields.Date(
        string='Week Start Date',
        compute='_compute_plan_week',
        store=True
    )
    plan_week_end = fields.Date(
        string='Week End Date',
        compute='_compute_plan_week',
        store=True
    )
    monday_meals = fields.Boolean(string='Monday', default=False)
    tuesday_meals = fields.Boolean(string='Tuesday', default=False)
    wednesday_meals = fields.Boolean(string='Wednesday', default=False)
    thursday_meals = fields.Boolean(string='Thursday', default=False)
    friday_meals = fields.Boolean(string='Friday', default=False)
    # Guest counts per weekday (only administrators should be able to set these)
    monday_guest_count = fields.Integer(string='Monday Guest Count', default=0)
    tuesday_guest_count = fields.Integer(string='Tuesday Guest Count', default=0)
    wednesday_guest_count = fields.Integer(string='Wednesday Guest Count', default=0)
    thursday_guest_count = fields.Integer(string='Thursday Guest Count', default=0)
    friday_guest_count = fields.Integer(string='Friday Guest Count', default=0)
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('submitted', 'Submitted'),
            ('confirmed', 'Confirmed'),
            ('cancel', 'Cancel')
        ],
        string='Status',
        default='draft'
    )
    reserved_day = fields.Char(
        string='Reserved Day',
        compute='_compute_reserved_day',
        store=True
    )

    # Compute reserved days
    @api.depends('monday_meals', 'tuesday_meals', 'wednesday_meals', 'thursday_meals', 'friday_meals',
                 'monday_guest_count', 'tuesday_guest_count', 'wednesday_guest_count',
                 'thursday_guest_count', 'friday_guest_count')
    def _compute_reserved_day(self):
        """Compute the reserved day(s) for the calendar."""
        for record in self:
            reserved_days = []
            if record.monday_meals:
                reserved_days.append('Monday')
            # include guest reservations as reserved days
            elif record.monday_guest_count and record.monday_guest_count > 0:
                reserved_days.append('Monday (Guest)')
            if record.tuesday_meals:
                reserved_days.append('Tuesday')
            elif record.tuesday_guest_count and record.tuesday_guest_count > 0:
                reserved_days.append('Tuesday (Guest)')
            if record.wednesday_meals:
                reserved_days.append('Wednesday')
            elif record.wednesday_guest_count and record.wednesday_guest_count > 0:
                reserved_days.append('Wednesday (Guest)')
            if record.thursday_meals:
                reserved_days.append('Thursday')
            elif record.thursday_guest_count and record.thursday_guest_count > 0:
                reserved_days.append('Thursday (Guest)')
            if record.friday_meals:
                reserved_days.append('Friday')
            elif record.friday_guest_count and record.friday_guest_count > 0:
                reserved_days.append('Friday (Guest)')
            record.reserved_day = ', '.join(reserved_days)

    # Compute week number and start/end dates
    @api.depends('week_date')
    def _compute_plan_week(self):
        """Compute the ISO week number and start/end dates from the selected date."""
        for record in self:
            if record.week_date:
                record.plan_week = record.week_date.isocalendar()[1]
                record.plan_week_begin = record.week_date - timedelta(days=record.week_date.weekday())
                record.plan_week_end = record.plan_week_begin + timedelta(days=6)
            else:
                record.plan_week = 0
                record.plan_week_begin = False
                record.plan_week_end = False

    @api.model
    def create(self, vals):
        """Override create method to generate a sequence number."""
        # Prevent non-admin users from creating guest reservations
        user = self.env.user
        is_admin = user.has_group('base.group_system')
        guest_keys = ['monday_guest_count', 'tuesday_guest_count', 'wednesday_guest_count',
                      'thursday_guest_count', 'friday_guest_count']
        if not is_admin:
            for k in guest_keys:
                if vals.get(k, 0) and int(vals.get(k, 0)) > 0:
                    raise UserError('Only administrators can create guest reservations.')

        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('lunch.week.plan') or 'New'
        return super(LunchWeekPlan, self).create(vals)

    def write(self, vals):
        """Override write to prevent non-admin users from setting guest counts."""
        user = self.env.user
        is_admin = user.has_group('base.group_system')
        guest_keys = ['monday_guest_count', 'tuesday_guest_count', 'wednesday_guest_count',
                      'thursday_guest_count', 'friday_guest_count']
        if not is_admin:
            for k in guest_keys:
                if k in vals and vals.get(k) and int(vals.get(k)) > 0:
                    raise UserError('Only administrators can set guest counts.')
        return super(LunchWeekPlan, self).write(vals)

    # Constraints to ensure valid week_date and no duplicate plans
    @api.constrains('week_date')
    def _check_week_date(self):
        """Ensure the target week is not in the past."""
        for record in self:
            # check week_date is not in the past
            if record.week_date < fields.Date.today():
                raise UserError("The target week cannot be in the past.")
            # check duplicate plan for the same week
            domain = [('employee_id', '=', record.employee_id.id), ('plan_week', '=', record.plan_week),
                      ('id', '!=', record.id), ('state', '!=', 'cancel')]
            #                                                                      ^ No comma here!
            existing_plans = self.search(domain)
            if existing_plans:
                raise UserError("You have already created a plan for this week.")

    # Action methods for state transitions with validations
    def action_submit(self):
        # check user is employee or not
        # allow administrators to submit plans on behalf of others
        if not self.env.user.has_group('base.group_system') and self.employee_id.user_id.id != self.env.user.id:
            raise UserError("You can only submit your own lunch plan.")
        """Submit the plan with validation logic."""
        today = fields.Date.today()
        WEDNESDAY = 2  # Weekday index for Wednesday
        if today.weekday() > WEDNESDAY:
            raise UserError("You can only submit lunch reservations before Wednesday for the next week!")

        plan_week = self.week_date.isocalendar()[1]
        current_week = today.isocalendar()[1]
        if plan_week != current_week + 1:
            raise UserError("You can only reserve lunch for the next week!")

        self.write({'state': 'submitted'})
        self.env['panexlogi.lunch.week.plan.summary'].update_summary_for_week(plan_week)

    # Cancel action
    def action_cancel(self):
        if self.state != 'draft':
            raise UserError("Only draft plans can be cancelled.")
        self.write({'state': 'cancel'})

    # Unsubmit action with validations
    def action_unsubmit(self):
        # check user is employee or not
        # allow administrators to unsubmit plans on behalf of others
        if not self.env.user.has_group('base.group_system') and self.employee_id.user_id.id != self.env.user.id:
            raise UserError("You can only unsubmit your own lunch plan.")
        """Revert the plan to draft state with validation logic."""
        today = fields.Date.today()
        plan_week = self.week_date.isocalendar()[1]
        current_week = today.isocalendar()[1]

        # Prevent unsubmission for the current or past weeks
        if plan_week <= current_week:
            raise UserError("You cannot unsubmit a plan for the current or past week!")

        # Ensure the plan is in the 'submitted' state
        if self.state != 'submitted':
            raise UserError("Only submitted plans can be reverted to draft.")

        # Revert the plan to draft state
        self.write({'state': 'draft'})
        self.env['panexlogi.lunch.week.plan.summary'].update_summary_for_week(plan_week)

    def action_confirm(self):
        """Confirm the plan."""
        if self.state != 'submitted':
            raise UserError("Only submitted plans can be confirmed.")
        self.write({'state': 'confirmed'})


#  Weekly Summary Model
class LunchWeekPlanSummary(models.Model):
    _name = 'panexlogi.lunch.week.plan.summary'
    _description = 'Employee Lunch Weekly Plan Summary'

    plan_week = fields.Integer(
        string='Week Number',
        compute='_compute_plan_week',
        store=True
    )
    plan_week_begin = fields.Date(
        string='Week Start Date',
        compute='_compute_plan_week',
        store=True
    )
    plan_week_end = fields.Date(
        string='Week End Date',
        compute='_compute_plan_week',
        store=True
    )
    monday_employees = fields.Many2many(
        'hr.employee',
        'lunch_week_plan_summary_monday_rel',  # Unique relation table name
        'summary_id',  # Column for the current model
        'employee_id',  # Column for the related model
        string='Monday Employees'
    )
    tuesday_employees = fields.Many2many(
        'hr.employee',
        'lunch_week_plan_summary_tuesday_rel',  # Unique relation table name
        'summary_id',  # Column for the current model
        'employee_id',  # Column for the related model
        string='Tuesday Employees'
    )
    wednesday_employees = fields.Many2many(
        'hr.employee',
        'lunch_week_plan_summary_wednesday_rel',  # Unique relation table name
        'summary_id',  # Column for the current model
        'employee_id',  # Column for the related model
        string='Wednesday Employees'
    )
    thursday_employees = fields.Many2many(
        'hr.employee',
        'lunch_week_plan_summary_thursday_rel',  # Unique relation table name
        'summary_id',  # Column for the current model
        'employee_id',  # Column for the related model
        string='Thursday Employees'
    )
    friday_employees = fields.Many2many(
        'hr.employee',
        'lunch_week_plan_summary_friday_rel',  # Unique relation table name
        'summary_id',  # Column for the current model
        'employee_id',  # Column for the related model
        string='Friday Employees'
    )
    total_monday = fields.Integer(string='Total Monday', compute='_compute_totals', store=True)
    total_tuesday = fields.Integer(string='Total Tuesday', compute='_compute_totals', store=True)
    total_wednesday = fields.Integer(string='Total Wednesday', compute='_compute_totals', store=True)
    total_thursday = fields.Integer(string='Total Thursday', compute='_compute_totals', store=True)
    total_friday = fields.Integer(string='Total Friday', compute='_compute_totals', store=True)
    total_week = fields.Integer(string='Total Week', compute='_compute_totals', store=True)
    # Totals coming from guest counts (set by administrators) - stored fields updated by update_summary_for_week
    total_monday_guests = fields.Integer(string='Monday Guests', default=0, store=True)
    total_tuesday_guests = fields.Integer(string='Tuesday Guests', default=0, store=True)
    total_wednesday_guests = fields.Integer(string='Wednesday Guests', default=0, store=True)
    total_thursday_guests = fields.Integer(string='Thursday Guests', default=0, store=True)
    total_friday_guests = fields.Integer(string='Friday Guests', default=0, store=True)

    def init(self):
        """Initialize or refresh the summary data."""
        try:
            # Delete all existing summaries
            self.search([]).unlink()

            # Get all unique week numbers with submitted plans
            week_numbers = self.env['panexlogi.lunch.week.plan'].search([
                ('state', '=', 'submitted')
            ]).mapped('plan_week')

            # Update summary for each week
            for week_number in set(week_numbers):
                self.update_summary_for_week(week_number)

        except Exception as e:
            raise UserError(f"Error initializing summary data: {str(e)}")

    # Compute week number and start/end dates
    def update_summary_for_week(self, week_number):
        """Update summary for a specific week"""
        # Find or create summary for this week
        summary = self.search([('plan_week', '=', week_number)], limit=1)
        if not summary:
            # Get week dates from any plan in this week
            week_plan = self.env['panexlogi.lunch.week.plan'].search(
                [('plan_week', '=', week_number)], limit=1
            )
            if week_plan:
                summary = self.create({
                    'plan_week': week_number,
                    'plan_week_begin': week_plan.plan_week_begin,
                    'plan_week_end': week_plan.plan_week_end,
                })
            else:
                return

        # Clear existing employee associations
        summary.write({
            'monday_employees': [(5, 0, 0)],
            'tuesday_employees': [(5, 0, 0)],
            'wednesday_employees': [(5, 0, 0)],
            'thursday_employees': [(5, 0, 0)],
            'friday_employees': [(5, 0, 0)],
        })

        # Get all submitted plans for this week
        plans = self.env['panexlogi.lunch.week.plan'].search([
            ('plan_week', '=', week_number),
            ('state', '=', 'submitted')
        ])

        # Add employees to respective days
        for plan in plans:
            if plan.monday_meals:
                summary.monday_employees = [(4, plan.employee_id.id)]
            # accumulate guest counts
            if plan.monday_guest_count:
                summary.total_monday_guests = (summary.total_monday_guests or 0) + int(plan.monday_guest_count)
            if plan.tuesday_meals:
                summary.tuesday_employees = [(4, plan.employee_id.id)]
            if plan.tuesday_guest_count:
                summary.total_tuesday_guests = (summary.total_tuesday_guests or 0) + int(plan.tuesday_guest_count)
            if plan.wednesday_meals:
                summary.wednesday_employees = [(4, plan.employee_id.id)]
            if plan.wednesday_guest_count:
                summary.total_wednesday_guests = (summary.total_wednesday_guests or 0) + int(plan.wednesday_guest_count)
            if plan.thursday_meals:
                summary.thursday_employees = [(4, plan.employee_id.id)]
            if plan.thursday_guest_count:
                summary.total_thursday_guests = (summary.total_thursday_guests or 0) + int(plan.thursday_guest_count)
            if plan.friday_meals:
                summary.friday_employees = [(4, plan.employee_id.id)]
            if plan.friday_guest_count:
                summary.total_friday_guests = (summary.total_friday_guests or 0) + int(plan.friday_guest_count)

    @api.depends('monday_employees', 'tuesday_employees', 'wednesday_employees', 'thursday_employees',
                 'friday_employees',
                 'total_monday_guests', 'total_tuesday_guests', 'total_wednesday_guests',
                 'total_thursday_guests', 'total_friday_guests')
    def _compute_totals(self):
        """Compute total meals for each day and the entire week."""
        for record in self:
            # base totals from employees
            emp_mon = len(record.monday_employees)
            emp_tue = len(record.tuesday_employees)
            emp_wed = len(record.wednesday_employees)
            emp_thu = len(record.thursday_employees)
            emp_fri = len(record.friday_employees)

            # guest totals (may be computed in update_summary_for_week)
            g_mon = record.total_monday_guests or 0
            g_tue = record.total_tuesday_guests or 0
            g_wed = record.total_wednesday_guests or 0
            g_thu = record.total_thursday_guests or 0
            g_fri = record.total_friday_guests or 0

            record.total_monday = emp_mon + g_mon
            record.total_tuesday = emp_tue + g_tue
            record.total_wednesday = emp_wed + g_wed
            record.total_thursday = emp_thu + g_thu
            record.total_friday = emp_fri + g_fri
            record.total_week = (
                record.total_monday +
                record.total_tuesday +
                record.total_wednesday +
                record.total_thursday +
                record.total_friday
            )

    def action_refresh_summary(self):
        """Action to manually refresh summary data for all weeks."""
        try:
            # Get all unique week numbers from submitted plans
            week_numbers = self.env['panexlogi.lunch.week.plan'].search([
                ('state', '=', 'submitted')
            ]).mapped('plan_week')
    
            # Update summary for each week
            for week_number in set(week_numbers):
                self.update_summary_for_week(week_number)
    
            # Return success notification
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Summary Refreshed',
                    'message': f'Successfully refreshed summary data for {len(set(week_numbers))} weeks',
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            raise UserError(f"Error refreshing summary data: {str(e)}")
