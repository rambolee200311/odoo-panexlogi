from odoo import http
from odoo.http import request
class GetWareHouseList(http.Controller):
    @http.route('/getWarehouseList', type='json', auth="user", cors="*", csrf=False)
    def getWarehouseList(self, **kw):
        # dingdan_h = 4900145711
        warehouses = request.env['stock.warehouse'].sudo().search([])  # 随便找个模型查询一条数据

        if not warehouses:
            back_data = {'code': 300, 'msg': 'warehouse 不存在'}
            return (back_data)

        wearhouselist = []
        for r in warehouses:
            wearhouse = {
                "id": r.id,
                "code": r.code,
                "name": r.name,
            }
            wearhouselist.append(wearhouse)
        data = {
            "result": wearhouselist
        }
        back_data = {'code': 100, 'msg': '查询warhouse成功', 'data': data}
        print("back_data==", back_data)
        return (back_data)