# -*- coding: utf-8 -*-
# from odoo import http


# class Test-project2(http.Controller):
#     @http.route('/test-project2/test-project2', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/test-project2/test-project2/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('test-project2.listing', {
#             'root': '/test-project2/test-project2',
#             'objects': http.request.env['test-project2.test-project2'].search([]),
#         })

#     @http.route('/test-project2/test-project2/objects/<model("test-project2.test-project2"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('test-project2.object', {
#             'object': obj
#         })

