from odoo import http, fields
from odoo.http import request


class GetProduct(http.Controller):
    @http.route('/getProduct', type='json', auth="user", cors="*", csrf=False)
    def getProduct(self, **kw):
        # dingdan_h = 4900145711

        domain = []
        product_id = 0
        product_param_id = kw.get('product_id')
        # print("product_==", product_)
        if product_param_id:
            product_id = int(product_param_id)
            domain.append(('id', '=', product_id))

        product_param_barcode = kw.get('barcode')
        if product_param_barcode:
            #productid_by_barcode = request.env['product.product'].sudo().search([('barcode', '=', product_param_barcode)])
            #product_id = productid_by_barcode.id
            domain.append(('barcode', '=', product_param_barcode))

        product_param_name = kw.get('name')
        if product_param_name:
            #productid_by_name = request.env['product.product'].sudo().search([('name', '=', product_param_name)])
            #product_id = productid_by_name.id
            domain.append(('name', '=', product_param_name))

        if not domain:
            back_data = {'code': 300, 'msg': 'product_id,name和barcode参数不能同时为空'}
            return (back_data)

        product_by_id = request.env['product.product'].sudo().search(domain)  # 随便找个模型查询一条数据

        # product_by_id = request.env['product.product'].sudo().search([('id', '=', product_id)])  # 随便找个模型查询一条数据

        if not product_by_id:
            back_data = {'code': 300, 'msg': 'product不存在'}
            return (back_data)

        listIds = []
        for r in product_by_id:
            singID = {
                "id": r.id,
                "code": r.code,
                "name": r.name,
                "barcode": r.barcode,
            }
            listIds.append(singID)
        data = {
            "product": listIds
        }
        back_data = {'code': 100, 'msg': '查询product成功', 'data': data}
        print("back_data==", back_data)
        return (back_data)
