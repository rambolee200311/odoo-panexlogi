# controllers/main.py
from odoo import http
from odoo.addons.auth_totp.controllers.home import HomeTFA

class HomeNoTrustDevice(HomeTFA):
    def _prepare_2fa_response(self, user, redirect_url):
        response = super()._prepare_2fa_response(user, redirect_url)
        # Forcefully disable trusted device logic
        response.qcontext['allow_trust_device'] = False
        return response

# Override the original controller
http.Controller.render = HomeNoTrustDevice().web_login