# -*- coding: utf-8 -*-
# from odoo import http


# class PanexLogi(http.Controller):
#     @http.route('/panex_logi/panex_logi', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/panex_logi/panex_logi/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('panex_logi.listing', {
#             'root': '/panex_logi/panex_logi',
#             'objects': http.request.env['panex_logi.panex_logi'].search([]),
#         })

#     @http.route('/panex_logi/panex_logi/objects/<model("panex_logi.panex_logi"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('panex_logi.object', {
#             'object': obj
#         })
