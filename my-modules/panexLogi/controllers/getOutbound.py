import requests
from odoo import http, fields
from odoo.http import request

class getOutboundOrderList(http.Controller):
    @http.route('/getOutboundOrderList', type='json', auth="user", cors="*", csrf=False)
    def getOutboundOrderList(self, **kw):
        # dingdan_h = 4900145711
        begin_date = '2000-01-01'
        domain = []

        if kw.get('begin_date'):
            begin_date = kw.get('begin_date')
            domain.append(('date', '>=', begin_date))

        end_date = fields.Date.today()
        if kw.get('end_date'):
            end_date = kw.get('end_date')
        domain.append(('date', '<=', end_date))

        if kw.get("warehouse_code"):
            warehouse_code = kw.get("warehouse_code")
            domain.append(('warehouse_code', '=', warehouse_code))

        if kw.get("project_code"):
            project_code = kw.get("project_code")
            domain.append(('project_code', '=', project_code))

        outbound_orders = request.env['panexlogi.outbound.order'].sudo().search(domain)

        if not outbound_orders:
            back_data = {'code': 300, 'msg': 'outbound order list不存在'}
            return (back_data)

        listIds = []
        for r in outbound_orders:
            singID = {
                "billno": r.billno,
                "date": r.date,
                "warehouse_code": r.warehouse_code,
                "project_code": r.project_code
            }
            listIds.append(singID)
        data = {
            "orders": listIds
        }
        back_data = {'code': 100, 'msg': '查询outbound order list成功', 'data': data}
        print("back_data==", back_data)
        return (back_data)
class GetOutboundOrder(http.Controller):
    @http.route('/getOutboundOrder', type='json', auth="user", cors="*", csrf=False)
    def getOutboundOrder(self, **kw):
        # dingdan_h = 4900145711
        billno = kw.get('billno')
        print("billno==", billno)
        outbound_order_by_billno = request.env['panexlogi.outbound.order'].sudo().search(
            [('billno', '=', billno)])  # 随便找个模型查询一条数据

        if not outbound_order_by_billno:
            back_data = {'code': 300, 'msg': 'outbound order不存在'}
            return (back_data)

        listIds = []
        for r in outbound_order_by_billno.outbound_order_product_ids:
            singID = {
                "product_id": r.product_id.id,
                "product_name": r.product_id.name,
                "batch": r.batch,
                "cntrno": r.cntrno,
                "pcs": r.pcs,
                "palletdno": r.palletdno
            }
            listIds.append(singID)
        data = {
            "billno": outbound_order_by_billno.billno,
            "date": outbound_order_by_billno.date,
            "products": listIds
        }
        back_data = {'code': 100, 'msg': '查询outbound order成功', 'data': data}
        print("back_data==", back_data)
        return (back_data)

    @http.route('/setOutboundOperate', type='json', auth="user", cors="*", csrf=False)
    def setOutboundOperate(self, **kw):
        outbound = kw.get('outbound')
        products = outbound["outbound_products"]  # kw.get('outbound_products')
        # print("outbound==", outbound)
        # print("products==", products)
        # stockPicks=open("stockPicks.json", "r")
        # listStockPicks=json.load(stockPicks)
        listIds = []
        for r in products:
            singID = (0, 0, {
                "product_id": r["product_id"],
                "pcs": r["pcs"]}
                      )
            listIds.append(singID)
        data = {
            "date": outbound["date"],
            "order_billno": request.env['panexlogi.outbound.order'].sudo().search(
                [('billno', '=', outbound["order_billno"])]).id,
            "remark": outbound["remark"],
            "outbound_operate_product_ids": listIds
        }
        print("data==", data)
        id = request.env['panexlogi.outbound.operate'].sudo().create(data)
        back_data = {'code': 100, 'msg': '新增outbound成功', 'data': id.billno}
        return (back_data)
