# -*- coding: utf-8 -*-
# from odoo import http


# class Test-common(http.Controller):
#     @http.route('/test-common/test-common', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/test-common/test-common/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('test-common.listing', {
#             'root': '/test-common/test-common',
#             'objects': http.request.env['test-common.test-common'].search([]),
#         })

#     @http.route('/test-common/test-common/objects/<model("test-common.test-common"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('test-common.object', {
#             'object': obj
#         })

