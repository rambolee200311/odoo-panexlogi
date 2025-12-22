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
        """Override write to prevent non-admin users from setting guest counts.
        user = self.env.user
        is_admin = user.has_group('base.group_system')
        guest_keys = ['monday_guest_count', 'tuesday_guest_count', 'wednesday_guest_count',
                     'thursday_guest_count', 'friday_guest_count']
        if not is_admin:
           for k in guest_keys:
               if k in vals and vals.get(k) and int(vals.get(k)) > 0:
                   raise UserError('Only administrators can set guest counts.')
        """

        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('lunch.week.plan') or 'New'
        record = super(LunchWeekPlan, self).create(vals)
        # If the state is updated to 'submitted', refresh the summary

        if vals.get('state') == 'submitted':
            plan_week = self.week_date.isocalendar()[1]
            self.env['panexlogi.lunch.week.plan.summary'].sudo().update_summary_for_week(plan_week)
        return record


    def write(self, vals):
        """Override write to prevent non-admin users from setting guest counts.
        user = self.env.user
        is_admin = user.has_group('base.group_system')
        guest_keys = ['monday_guest_count', 'tuesday_guest_count', 'wednesday_guest_count',
                      'thursday_guest_count', 'friday_guest_count']
        if not is_admin:
            for k in guest_keys:
                if k in vals and vals.get(k) and int(vals.get(k)) > 0:
                    raise UserError('Only administrators can set guest counts.')
        """
        record = super(LunchWeekPlan, self).write(vals)
        # If wrote with submitted state, refresh summary
        '''
        if vals.get('state') == 'submitted':
            self.env['panexlogi.lunch.week.plan.summary'].sudo().update_summary_for_week(record.plan_week)
        return record
        '''

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
    def action_submit_old(self):
        # check user is employee or not
        # allow administrators to submit plans on behalf of others

        if not self.env.user.has_group('base.group_system') and self.employee_id.user_id.id != self.env.user.id:
            raise UserError("You can only submit your own lunch plan.")
        """Submit the plan with validation logic."""
        today = fields.Date.today()
        WEDNESDAY = 3  # Weekday index for Wednesday
        if today.weekday() > WEDNESDAY:
            raise UserError("You can only submit lunch reservations before Wednesday for the next week!")

        plan_week = self.week_date.isocalendar()[1]
        current_week = today.isocalendar()[1]
        if plan_week != current_week + 1:
            raise UserError("You can only reserve lunch for the next week!")

        # find guests if not create one
        '''
        guest_model = self.env['panexlogi.lunch.guest']
        guest_names = f"{self.employee_id.name}'s Guests"
        existing_guest = guest_model.search([('name', '=', guest_names)], limit=1)
        if not existing_guest and (self.monday_guest_count > 0 or self.tuesday_guest_count > 0 or
                                   self.wednesday_guest_count > 0 or self.thursday_guest_count > 0 or
                                   self.friday_guest_count > 0):
            guest_model.create({'name': guest_names})
        '''
        self.write({'state': 'submitted'})
        self.env.cr.flush()
        plan_week = self.week_date.isocalendar()[1]
        self.env['panexlogi.lunch.week.plan.summary'].sudo().update_summary_for_week(plan_week)

    def action_submit(self):
        # Check if user is employee or not
        # Allow administrators to submit plans on behalf of others
        
        if not self.env.user.has_group('base.group_system') and self.employee_id.user_id.id != self.env.user.id:
            raise UserError("You can only submit your own lunch plan.")
        
        """Submit the plan with validation logic."""
        today = fields.Date.today()
        WEDNESDAY = 3  # Weekday index for Wednesday
        
        # Check 1: Must submit before Wednesday
        if today.weekday() > WEDNESDAY:
            raise UserError("You can only submit lunch reservations before Wednesday for the next week!")
        
        # Check 2: Must reserve for the next week
        # Using week_start_date to compare
        week_start_date = self.plan_week_begin
        
        # Calculate next Monday
        days_until_next_monday = (7 - today.weekday()) % 7 or 7
        next_monday = today + timedelta(days=days_until_next_monday)
        
        if week_start_date != next_monday:
            raise UserError("You can only reserve lunch for the next week!")
        
        # Check 3: Ensure the week is in the future
        if week_start_date <= today:
            raise UserError("You can only reserve lunch for future weeks!")
        
        # Find or create guest records if needed
        '''
        guest_model = self.env['panexlogi.lunch.guest']
        guest_names = f"{self.employee_id.name}'s Guests"
        existing_guest = guest_model.search([('name', '=', guest_names)], limit=1)
        if not existing_guest and (self.monday_guest_count > 0 or self.tuesday_guest_count > 0 or
                                self.wednesday_guest_count > 0 or self.thursday_guest_count > 0 or
                                self.friday_guest_count > 0):
            guest_model.create({'name': guest_names})
        '''
        
        # Update state
        self.write({'state': 'submitted'})
        self.env.cr.flush()
        
        # Update summary
        plan_week = self.plan_week_begin.isocalendar()[1]
        self.env['panexlogi.lunch.week.plan.summary'].sudo().update_summary_for_week(plan_week)
        
        return True

    # Cancel action
    def action_cancel(self):
        if self.state != 'draft':
            raise UserError("Only draft plans can be cancelled.")
        self.write({'state': 'cancel'})

    # Unsubmit action with validations
    def action_unsubmit_old(self):
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
        self.env.cr.flush()
        plan_week = self.week_date.isocalendar()[1]
        self.env['panexlogi.lunch.week.plan.summary'].sudo().update_summary_for_week(plan_week)

    def action_confirm(self):
        """Confirm the plan."""
        if self.state != 'submitted':
            raise UserError("Only submitted plans can be confirmed.")
        self.write({'state': 'confirmed'})
        
    def action_unsubmit(self):
        # Check if user is employee or not
        # Allow administrators to unsubmit plans on behalf of others
        if not self.env.user.has_group('base.group_system') and self.employee_id.user_id.id != self.env.user.id:
            raise UserError("You can only unsubmit your own lunch plan.")
        
        """Revert the plan to draft state with validation logic."""
        today = fields.Date.today()
        
        # Check 1: Ensure the plan is in the 'submitted' state
        if self.state != 'submitted':
            raise UserError("Only submitted plans can be reverted to draft.")
        
        # Check 2: Prevent unsubmission for the current or past weeks
        # Use the correct field name - based on your previous code, it should be plan_week_begin
        week_start_date = self.plan_week_begin  # Changed from self.week_date
        
        if not week_start_date:
            raise UserError("Week start date is not set!")
        
        # Calculate Monday of the current week
        days_since_monday = today.weekday()  # Monday=0, Sunday=6
        current_monday = today - timedelta(days=days_since_monday)
        
        # Compare dates directly instead of week numbers
        if week_start_date <= current_monday:
            raise UserError("You cannot unsubmit a plan for the current or past week!")
        
        # Additional check: If today is Wednesday or later, cannot unsubmit for next week
        WEDNESDAY = 3  # Monday=0, Wednesday=2
        
        # Check if the plan is for next week and today is Wednesday or later
        if today.weekday() >= WEDNESDAY:
            # Calculate next Monday
            days_until_next_monday = (7 - today.weekday()) % 7 or 7
            next_monday = today + timedelta(days=days_until_next_monday)
            
            if week_start_date == next_monday:
                raise UserError("You cannot modify next week's plan after Wednesday!")
        
        # Revert the plan to draft state
        self.write({'state': 'draft'})
        self.env.cr.flush()
        
        # Update summary with the correct field
        plan_week = self.plan_week_begin.isocalendar()[1]  # Changed from self.week_date
        self.env['panexlogi.lunch.week.plan.summary'].sudo().update_summary_for_week(plan_week)
        
        return True

# Weekly Summary Model
class LunchWeekPlanSummary(models.Model):
    _name = 'panexlogi.lunch.week.plan.summary'
    _description = 'Employee Lunch Weekly Plan Summary'

    plan_week = fields.Integer(
        string='Week Number',
        required=True
    )
    plan_week_begin = fields.Date(
        string='Week Start Date',
        required=True
    )
    plan_week_end = fields.Date(
        string='Week End Date',
        required=True
    )
    monday_employees = fields.Many2many(
        'hr.employee',
        'lunch_week_plan_summary_monday_rel',
        'summary_id',
        'employee_id',
        string='Monday Employees'
    )

    tuesday_employees = fields.Many2many(
        'hr.employee',
        'lunch_week_plan_summary_tuesday_rel',
        'summary_id',
        'employee_id',
        string='Tuesday Employees'
    )
    wednesday_employees = fields.Many2many(
        'hr.employee',
        'lunch_week_plan_summary_wednesday_rel',
        'summary_id',
        'employee_id',
        string='Wednesday Employees'
    )
    thursday_employees = fields.Many2many(
        'hr.employee',
        'lunch_week_plan_summary_thursday_rel',
        'summary_id',
        'employee_id',
        string='Thursday Employees'
    )
    friday_employees = fields.Many2many(
        'hr.employee',
        'lunch_week_plan_summary_friday_rel',
        'summary_id',
        'employee_id',
        string='Friday Employees'
    )
    '''
    monday_guests = fields.Many2many(
        'panexlogi.lunch.guest',
        'lunch_week_plan_summary_monday_guest_rel',
        'summary_id',
        'id',
        string='Monday Guests'
    )
    tuesday_guests = fields.Many2many(
        'panexlogi.lunch.guest',
        'lunch_week_plan_summary_tuesday_guest_rel',
        'summary_id',
        'id',
        string='Tuesday Guests'
    )

    wednesday_guests = fields.Many2many(
        'panexlogi.lunch.guest',
        'lunch_week_plan_summary_wednesday_guest_rel',
        'summary_id',
        'id',
        string='Wednesday Guests'
    )

    thursday_guests = fields.Many2many(
        'panexlogi.lunch.guest',
        'lunch_week_plan_summary_thursday_guest_rel',
        'summary_id',
        'id',
        string='Thursday Guests'
    )

    friday_guests = fields.Many2many(
        'panexlogi.lunch.guest',
        'lunch_week_plan_summary_friday_guest_rel',
        'summary_id',
        'id',
        string='Friday Guests'
    )
    '''

    total_monday = fields.Integer(string='Total Monday', compute='_compute_totals', store=True)
    total_tuesday = fields.Integer(string='Total Tuesday', compute='_compute_totals', store=True)
    total_wednesday = fields.Integer(string='Total Wednesday', compute='_compute_totals', store=True)
    total_thursday = fields.Integer(string='Total Thursday', compute='_compute_totals', store=True)
    total_friday = fields.Integer(string='Total Friday', compute='_compute_totals', store=True)
    total_week = fields.Integer(string='Total Week', compute='_compute_totals', store=True)

    # Guest counts - reset to 0 each time summary is updated
    total_monday_guests = fields.Integer(string='Monday Guests', default=0)
    total_tuesday_guests = fields.Integer(string='Tuesday Guests', default=0)
    total_wednesday_guests = fields.Integer(string='Wednesday Guests', default=0)
    total_thursday_guests = fields.Integer(string='Thursday Guests', default=0)
    total_friday_guests = fields.Integer(string='Friday Guests', default=0)

    @api.model
    def init(self):
        """Initialize or refresh the summary data."""
        try:
            # Get all unique week numbers with submitted plans
            week_numbers = self.env['panexlogi.lunch.week.plan'].search([
                ('state', '=', 'submitted')
            ]).mapped('plan_week')

            # Update summary for each week
            for week_number in set(week_numbers):
                self.update_summary_for_week(week_number)

        except Exception as e:
            raise UserError(f"Error initializing summary data: {str(e)}")

    def update_summary_for_week(self, week_number):
        """Update summary for a specific week."""
        try:
            # Find or create the summary for the given week
            summary = self.search([('plan_week', '=', week_number)], limit=1)
            week_plan = self.env['panexlogi.lunch.week.plan'].search(
                [('plan_week', '=', week_number)], limit=1
            )

            if not week_plan:
                raise UserError(f"No lunch plans found for week {week_number}.")

            if summary:
                # Reset existing summary data
                summary.write({
                    'plan_week_begin': week_plan.plan_week_begin,
                    'plan_week_end': week_plan.plan_week_end,
                    'monday_employees': [(5,)],
                    'tuesday_employees': [(5,)],
                    'wednesday_employees': [(5,)],
                    'thursday_employees': [(5,)],
                    'friday_employees': [(5,)],
                    'total_monday_guests': 0,
                    'total_tuesday_guests': 0,
                    'total_wednesday_guests': 0,
                    'total_thursday_guests': 0,
                    'total_friday_guests': 0,
                })
            else:
                summary = self.create({
                    'plan_week': week_number,
                    'plan_week_begin': week_plan.plan_week_begin,
                    'plan_week_end': week_plan.plan_week_end,
                })

            # Collect data from all submitted plans for the week
            plans = self.env['panexlogi.lunch.week.plan'].search([
                ('plan_week', '=', week_number),
                ('state', '=', 'submitted')
            ])

            employee_assignments = {
                'monday': set(),
                'tuesday': set(),
                'wednesday': set(),
                'thursday': set(),
                'friday': set(),
            }
            guest_counts = {
                'monday': 0,
                'tuesday': 0,
                'wednesday': 0,
                'thursday': 0,
                'friday': 0,
            }

            for plan in plans:
                # Assign employees and count guests for each day
                if plan.monday_meals:
                    employee_assignments['monday'].add(plan.employee_id.id)
                guest_counts['monday'] += plan.monday_guest_count or 0

                if plan.tuesday_meals:
                    employee_assignments['tuesday'].add(plan.employee_id.id)
                guest_counts['tuesday'] += plan.tuesday_guest_count or 0

                if plan.wednesday_meals:
                    employee_assignments['wednesday'].add(plan.employee_id.id)
                guest_counts['wednesday'] += plan.wednesday_guest_count or 0

                if plan.thursday_meals:
                    employee_assignments['thursday'].add(plan.employee_id.id)
                guest_counts['thursday'] += plan.thursday_guest_count or 0

                if plan.friday_meals:
                    employee_assignments['friday'].add(plan.employee_id.id)
                guest_counts['friday'] += plan.friday_guest_count or 0

            # Update summary with collected data
            summary.write({
                'monday_employees': [(6, 0, list(employee_assignments['monday']))],
                'tuesday_employees': [(6, 0, list(employee_assignments['tuesday']))],
                'wednesday_employees': [(6, 0, list(employee_assignments['wednesday']))],
                'thursday_employees': [(6, 0, list(employee_assignments['thursday']))],
                'friday_employees': [(6, 0, list(employee_assignments['friday']))],
                'total_monday_guests': guest_counts['monday'],
                'total_tuesday_guests': guest_counts['tuesday'],
                'total_wednesday_guests': guest_counts['wednesday'],
                'total_thursday_guests': guest_counts['thursday'],
                'total_friday_guests': guest_counts['friday'],
            })
            # Recompute totals
            summary._compute_totals()

        except Exception as e:
            raise UserError(f"Error updating summary for week {week_number}: {str(e)}")

    @api.depends('monday_employees', 'tuesday_employees', 'wednesday_employees', 'thursday_employees',
                 'friday_employees', 'total_monday_guests', 'total_tuesday_guests', 'total_wednesday_guests',
                 'total_thursday_guests', 'total_friday_guests')
    def _compute_totals(self):
        """Compute total meals for each day and the entire week."""
        for record in self:
            # Calculate totals for each day
            record.total_monday = len(record.monday_employees) + record.total_monday_guests
            record.total_tuesday = len(record.tuesday_employees) + record.total_tuesday_guests
            record.total_wednesday = len(record.wednesday_employees) + record.total_wednesday_guests
            record.total_thursday = len(record.thursday_employees) + record.total_thursday_guests
            record.total_friday = len(record.friday_employees) + record.total_friday_guests

            # Calculate total for the week
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
            # First clear all existing summary records
            '''
            existing_summaries = self.search([])
            if existing_summaries:
                existing_summaries.unlink()
            '''
            # Ensure delete operation is committed to database
            self.env.cr.flush()

            # Get all unique week numbers from submitted plans
            week_numbers = self.env['panexlogi.lunch.week.plan'].search([
                ('state', '=', 'submitted')
            ]).mapped('plan_week')

            # Create/update summary for each week with submitted plans
            for week_number in set(week_numbers):
                self.env['panexlogi.lunch.week.plan.summary'].sudo().update_summary_for_week(week_number)
                # Flush again to ensure all changes are committed
                self.env.cr.flush()

            # Return success notification
            week_count = len(set(week_numbers))
            message = f'Successfully refreshed summary data for {week_count} weeks' if week_count > 0 else 'No submitted plans found to refresh'

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Summary Refreshed',
                    'message': message,
                    'type': 'success' if week_count > 0 else 'warning',
                    'sticky': False,
                }
            }
        except Exception as e:
            raise UserError(f"Error refreshing summary data: {str(e)}")

    def action_print_summary_report(self):
        """Generate a report for the selected summaries."""
        return self.env.ref('panexLogi.action_lunch_week_plan_summary_report').report_action(self)


class GuestOfLunch(models.Model):
    _name = 'panexlogi.lunch.guest'
    _description = 'Guest Lunch'

    name = fields.Char(
        string='Guest Name',
        readonly=True
    )
