# -*- coding: utf-8 -*-
# from odoo import http


# class Test-project1(http.Controller):
#     @http.route('/test-project1/test-project1', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/test-project1/test-project1/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('test-project1.listing', {
#             'root': '/test-project1/test-project1',
#             'objects': http.request.env['test-project1.test-project1'].search([]),
#         })

#     @http.route('/test-project1/test-project1/objects/<model("test-project1.test-project1"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('test-project1.object', {
#             'object': obj
#         })

