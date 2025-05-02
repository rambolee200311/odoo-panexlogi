import logging
import requests
import time
from odoo import models, fields, api
from requests.exceptions import RequestException

_logger = logging.getLogger(__name__)


class CustomerTemp(models.Model):
    _name = 'panexlogi.customer.temp'
    _description = 'Temporary Customer Data'
    _rec_name = 'customer_name'

    # Fields
    customer_name = fields.Char(string='Customer Name', required=True)
    kvknr = fields.Char(string='KvKnr')
    street = fields.Char(string='Street')
    zip = fields.Char(string='ZIP')
    city = fields.Char(string='City')
    country_name = fields.Char(string='Country Name')
    state = fields.Many2one('res.country.state', string='State')
    country = fields.Many2one('res.country', string='Country')
    phone = fields.Char(string='Phone')
    mobile = fields.Char(string='Mobile')
    fax = fields.Char(string='Fax')
    email = fields.Char(string='Email')
    website = fields.Char(string='Website')
    vat = fields.Char(string='Tax ID')
    iban = fields.Char(string='IBAN')
    bic = fields.Char(string='BIC')
    processed = fields.Boolean(string='Processed', default=False)

    @api.model_create_multi
    def create(self, vals_list):
        """Batch creation with deduplication and asynchronous geocoding."""
        unique_vals = self._deduplicate_vals(vals_list)
        records = super().create(unique_vals)
        #for record in records:
            # 异步执行地址解析（避免阻塞事务）
        #    record._fetch_google_maps_details()
        return records

    """Remove duplicate entries based on unique keys."""
    def _deduplicate_vals(self, vals_list):
        seen = set()
        unique_vals = []

        for vals in vals_list:
            unique_key = (
                vals.get('customer_name', '').strip().lower()
            )

            if unique_key not in seen:
                seen.add(unique_key)
                unique_vals.append(vals)

        return unique_vals

    def action_update_partner(self):
        """Action to update partner for the selected record."""
        #self.ensure_one()  # Ensure only one record is selected
        self._update_partners()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': 'Partner updated successfully.',
                'sticky': False,
            },
        }
    def _update_partners(self):
        """Update partners with the latest data."""
        for record in self:
            if record.processed:
                continue

            # Search for an existing partner
            partner = self.env['res.partner'].search([
                ('name', 'ilike', record.customer_name)
            ], limit=1)

            if partner:
                # Update existing partner
                partner.write({
                    'street': record.street,
                    'zip': record.zip,
                    'city': record.city,
                    'country_id': record.country.id if record.country else False,
                    'state_id': record.state.id if record.state else False,
                    'phone': record.phone,
                    'mobile': record.mobile,
                    'x_fax': record.fax,
                    'email': record.email,
                    'website': record.website,
                    'is_company': True,
                    'vat': record.vat,
                    'x_kvknr': record.kvknr,
                })
                # Create or update bank account
                record._create_bank_account(record.bic, record.iban, partner)
            else:
                # Create a new partner
                partner = self.env['res.partner'].create({
                    'name': record.customer_name,
                    'street': record.street,
                    'zip': record.zip,
                    'city': record.city,
                    'country_id': record.country.id if record.country else False,
                    'state_id': record.state.id if record.state else False,
                    'phone': record.phone,
                    'mobile': record.mobile,
                    'x_fax': record.fax,
                    'email': record.email,
                    'website': record.website,
                    'is_company': True,
                    'vat': record.vat,
                    'x_kvknr': record.kvknr,
                })
                # Create bank account
                record._create_bank_account(record.bic, record.iban, partner)

            # Mark record as processed
            record.processed = True

    def _create_bank_account(self, bic, iban, partner):
        """Create or update a bank account for the partner."""
        if bic:
            # Search or create the bank
            bank = self.env['res.bank'].search([('bic', '=', bic)], limit=1)
            if not bank:
                bank = self.env['res.bank'].create({
                    'name': bic,
                    'bic': bic,
                })

            # Search or create the bank account
            if iban:
                account = self.env['res.partner.bank'].search([
                    ('partner_id', '=', partner.id),
                    ('acc_number', '=', iban)
                ], limit=1)
                if not account:
                    self.env['res.partner.bank'].create({
                        'acc_holder_name': partner.name,
                        'partner_id': partner.id,
                        'acc_number': iban,
                        'bank_id': bank.id,
                    })

    def action_batch_update_google_maps_details(self):
        """Batch update Google Maps details for all selected records."""
        for record in self:
            record._fetch_google_maps_details()

    def _fetch_google_maps_details(self):
        """Fetch and update address details using Google Maps API."""
        self.ensure_one()
        api_key = self.env['ir.config_parameter'].sudo().get_param('base_geolocalize.google_map_api_key')

        if not api_key:
            _logger.warning("Google Maps API key missing")
            return

        # Prepare address parts
        address_parts = list(filter(None, [
            self.street,
            self.zip,
            self.city,
            self.country_name,
        ]))

        if not address_parts:
            _logger.warning("No address parts available for geocoding")
            return

        # Retry logic
        max_retries = 3
        retry_delay = 2  # seconds

        for attempt in range(max_retries):
            try:
                response = requests.get(
                    "https://maps.googleapis.com/maps/api/geocode/json",
                    params={'address': ','.join(address_parts), 'key': api_key},
                    timeout=15
                )
                response.raise_for_status()
                data = response.json()

                if data.get('status') == 'OK':
                    self._process_geocode_result(data['results'][0])
                    break  # Exit the loop if the status is OK
                else:
                    _logger.warning("Attempt %d: Google Maps API returned status: %s", attempt + 1, data.get('status'))

            except requests.RequestException as e:
                _logger.error("Attempt %d: Geocoding failed: %s", attempt + 1, str(e))

            if attempt < max_retries - 1:
                time.sleep(retry_delay)  # Wait before retrying
        else:
            _logger.error("Failed to fetch data from Google Maps API after %d attempts", max_retries)

    def _process_geocode_result(self, result):
        """Process the geocoding result and update fields."""
        components = {comp['types'][0]: comp for comp in result['address_components']}

        # Update street
        #self.street = components.get('route', {}).get('long_name', self.street)

        # Update ZIP
        if not self.zip:
            self.zip = components.get('postal_code', {}).get('long_name', self.zip) or \
                       components.get('postal_code_prefix', {}).get('long_name', self.zip)

        # Update city
        if not self.city:
            self.city = components.get('locality', {}).get('long_name') or \
                        components.get('administrative_area_level_2', {}).get('long_name') or \
                        components.get('administrative_area_level_3', {}).get('long_name') or \
                        self.city

        # Update country and state
        if 'country' in components:
            country_code = components['country']['short_name']
            country = self.env['res.country'].search([('code', 'ilike', country_code)], limit=1)
            if country:
                self.country = country.id
                self._update_state(components, country)

    def _update_state(self, components, country):
        """Update state information based on geocoding result."""
        state_name = components.get('administrative_area_level_1', {}).get('long_name')
        state_code = components.get('administrative_area_level_1', {}).get('short_name')

        if state_name and state_code and country:
            # Search for an existing state with the same country and code
            state = self.env['res.country.state'].search([
                ('code', '=', state_code),
                ('country_id', '=', country.id)
            ], limit=1)

            if state:
                """
                # Create a new state if it doesn't exist
                state = self.env['res.country.state'].create({
                    'name': state_name,
                    'code': state_code,
                    'country_id': country.id
                })
                """
                self.state = state.id

    def action_update_partner_new(self):
        """Update partner details using Google Maps API for incomplete records."""
        api_key = self.env['ir.config_parameter'].sudo().get_param('base_geolocalize.google_map_api_key')
        if not api_key:
            _logger.warning("Google Maps API key is missing")
            return

        partners = self.env['res.partner'].search([
            '|', ('street', '=', False), ('zip', '=', False),
            '|', ('city', '=', False), ('country_id', '=', False)
        ])

        for partner in partners:
            address_parts = list(filter(None, [
                partner.name,
                partner.street,
                partner.zip,
                partner.city,
                partner.country_id.name if partner.country_id else '',
            ]))

            if not address_parts:
                _logger.warning("No address parts available for geocoding for partner: %s", partner.name)
                continue

            try:
                response = requests.get(
                    "https://maps.googleapis.com/maps/api/geocode/json",
                    params={'address': ','.join(address_parts), 'key': api_key},
                    timeout=15
                )
                response.raise_for_status()
                data = response.json()

                if data.get('status') == 'OK':
                    result = data['results'][0]
                    components = {comp['types'][0]: comp for comp in result['address_components']}

                    # Update ZIP
                    if not partner.zip:
                        partner.zip = components.get('postal_code', {}).get('long_name', partner.zip)

                    # Update city
                    if not partner.city:
                        partner.city = components.get('locality', {}).get('long_name') or \
                                       components.get('administrative_area_level_2', {}).get('long_name') or \
                                       components.get('administrative_area_level_3', {}).get('long_name')

                    # Update country and state
                    if 'country' in components:
                        country_code = components['country']['short_name']
                        country = self.env['res.country'].search([('code', 'ilike', country_code)], limit=1)
                        if country:
                            partner.country_id = country.id
                            state_name = components.get('administrative_area_level_1', {}).get('long_name')
                            state_code = components.get('administrative_area_level_1', {}).get('short_name')

                            if state_name and state_code:
                                state = self.env['res.country.state'].search([
                                    ('code', '=', state_code),
                                    ('country_id', '=', country.id)
                                ], limit=1)
                                if state:
                                    partner.state_id = state.id
                else:
                    _logger.warning("Google Maps API returned status: %s for partner: %s", data.get('status'),
                                    partner.name)

            except RequestException as e:
                _logger.error("Geocoding failed for partner: %s, error: %s", partner.name, str(e))




