# 测试获取session_id
import requests
from odoo import http
from odoo.http import request
from odoo.tools import json


class GetToken(http.Controller):

    def getOdooToken(self, login, password):
        # http://localhost:8088访问odoo的路径，后面的web/session/authenticate固定写法请不要动！！！

        url = "http://localhost:8088/web/session/authenticate"
        # url = "http://localhost:8069/web/session/authenticate"
        # 传入需要访问的数据库名称，登录账号与密码 panexDB
        data = {
            "params": {
                "db": "odoo172",
                "login": login,
                "password": password,
            }
        }
        headers = {'Content-type': 'application/json'}
        response = requests.post(url, headers=headers, json=data)
        # 从服务器返回的响应信息中获取名为"session_id"的cookie的值，并将其返回。
        return response.cookies["session_id"]

    @http.route('/getToken', type='json', auth="none", cors="*", csrf=False)
    def getToken(self, **kw):
        login = kw.get("login")
        password = kw.get("password")
        odootoken = self.getOdooToken(login, password)
        return odootoken
        # 用此代码进行接口测试，查看前端是否拿到了session_id

    @http.route('/getPacklist', type='json', auth="user", cors="*", csrf=False)
    def getPacklist(self, **kw):
        # dingdan_h = 4900145711
        billno = kw.get('billno')
        print("billno==", billno)
        packlist_by_billno = request.env['panexlogi.waybill.packlist'].sudo().search(
            [('billno', '=', billno)])  # 随便找个模型查询一条数据

        if not packlist_by_billno:
            back_data = {'code': 300, 'msg': 'packing list不存在'}
            return (back_data)
        data = {
            "billno": packlist_by_billno.billno,
            "product_id": packlist_by_billno.product_id.default_code,
            "product_name": packlist_by_billno.product_id.name,
            "pcs": packlist_by_billno.pcs,
            "waybillno": packlist_by_billno.waybillno,
        }
        back_data = {'code': 100, 'msg': '查询packing list成功', 'data': data}
        print("back_data==", back_data)
        return (back_data)

    @http.route('/setStockPicking', type='json', auth="user", cors="*", csrf=False)
    def setStockPicking(self, **kw):
        stockPicks = kw.get('stockpicks')
        # listStockPicks=json.load(stockPicks)
        listIds = []
        for r in stockPicks:
            data = {
                "barcode": r["barcode"],
                "prouduct_id": r["prouduct_id"],
                "qty": r["qty"]
            }
            id = request.env['panexlogi.demostockpicking'].sudo().create(data)
            singID = {
                "id": id.id,
                "billno": id.billno
            }
            listIds.append(singID)
        back_data = {'code': 100, 'msg': '新增stock picking成功', 'data': listIds}
        return (back_data)
