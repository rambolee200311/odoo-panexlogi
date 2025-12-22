import logging
from odoo import _, models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PaymentApplicationDeepSeek(models.Model):
    _inherit = 'panexlogi.finance.paymentapplication'

    check_result = fields.Text(string="DeepSeek Check Results", readonly=True)
    check_time_begin = fields.Datetime(string="DeepSeek Check Start Time", readonly=True)
    check_duration = fields.Float(string="DeepSeek Check Duration (seconds)", readonly=True)
    check_status = fields.Selection([
        ('pass', 'Passed'),
        ('warning', 'Needs Attention'),
        ('error', 'Issues Found'),
        ('unknown', 'Unknown')
    ], string="Check Status", readonly=True)
    risk_level = fields.Selection([
        ('none', 'No Risk'),
        ('low', 'Low Risk'),
        ('medium', 'Medium Risk'),
        ('high', 'High Risk'),
        ('unknown', 'Unknown')
    ], string="Risk Level", readonly=True, default='unknown')

    def action_deepseek_check(self):
        """
        Call DeepSeek check service with user-friendly results
        
        Returns:
            dict: Odoo action for result notification
        """
        self.ensure_one()
        
        # Initialize utilities
        deepseek_checker = self.env['deepseek.checker']
        deepseek_utils = self.env['deepseek.utils']
        
        # Set start time
        self.check_time_begin = fields.Datetime.now()
        self.check_result = False
        self.check_status = 'unknown'
        self.risk_level = 'unknown'
        self.check_duration = 0.0
        try:
            # Prepare data for DeepSeek check
            order_data = self._prepare_order_data()
            attachments = deepseek_utils.prepare_attachments(self, self.paymentapplicationline_ids)

            # Execute DeepSeek check
            result = deepseek_checker.check_order_with_deepseek(order_data, attachments)

            # Calculate and store duration
            self.check_duration = (fields.Datetime.now() - self.check_time_begin).total_seconds()

            # Store results
            deepseek_utils.store_check_results(self, result)

            # Return user-friendly notification
            return deepseek_utils.show_result_notification(result)

        except Exception as e:
            _logger.error("DeepSeek check failed for payment application %s: %s", self.id, str(e))
            return deepseek_utils.show_error_notification(str(e))

    def action_view_check_details(self):
        """
        Action to view detailed check results
        
        Returns:
            dict: Odoo client action for notification
            
        Raises:
            UserError: If no check results available
        """
        self.ensure_one()

        if not self.check_result:
            raise UserError(_("No check results available. Please run the DeepSeek check first."))

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Check Details',
                'message': self.check_result,
                'type': 'info',
                'sticky': True,
            }
        }
        
    def _prepare_order_data(self):
        """
        Prepare order data for DeepSeek check
        
        Returns:
            dict: Structured order data
        """
        self.ensure_one()
        
        data = {
            'payment_application_id': self.id,
            'billno': self.billno,
            'total_amount': self.total_amount,
            'payee': {
                'id': self.payee.id,
                'name': self.payee.name,
            },
            'invoiceno': self.invoiceno,
            'invoice_date': self._format_date(self.invoice_date),
            'due_date': self._format_date(self.due_date),
            'remarks': self.remark or '',
            'line_items': self._prepare_line_items(),
        }
        
        _logger.debug("Prepared order data for DeepSeek check: %s", data)
        return data

    def _prepare_line_items(self):
        """Prepare line items data"""
        line_items = []
        for line in self.paymentapplicationline_ids:
            line_items.append({
                'fitem': line.fitem.id if line.fitem else None,
                'fitem_name': line.fitem_name or '',
                'amount': line.amount,
                'remark': line.remark or '',
            })
        return line_items

    def _format_date(self, date_field):
        """Safely format date field to string"""
        return str(date_field) if date_field else None

    def action_retry_check(self):
        """
        Retry DeepSeek check
        
        Returns:
            dict: Result of action_deepseek_check
        """
        self.ensure_one()
        return self.action_deepseek_check()