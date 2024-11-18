# -*- coding: utf-8 -*-
# from odoo import http


# class Jsdemo(http.Controller):
#     @http.route('/jsdemo/jsdemo', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/jsdemo/jsdemo/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('jsdemo.listing', {
#             'root': '/jsdemo/jsdemo',
#             'objects': http.request.env['jsdemo.jsdemo'].search([]),
#         })

#     @http.route('/jsdemo/jsdemo/objects/<model("jsdemo.jsdemo"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('jsdemo.object', {
#             'object': obj
#         })

