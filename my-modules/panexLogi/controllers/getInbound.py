import requests
from odoo import http, fields
from odoo.http import request


class getInboundOrderList(http.Controller):
    @http.route('/getInboundOrderList', type='json', auth="user", cors="*", csrf=False)
    def getInboundOrderList(self, **kw):
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

        inbound_orders = request.env['panexlogi.inbound.order'].sudo().search(domain)

        if not inbound_orders:
            back_data = {'code': 300, 'msg': 'inbound order list不存在'}
            return (back_data)

        listIds = []
        for r in inbound_orders:
            singID = {
                "billno": r.billno,
                "date": r.date,
                "waybillno": r.waybillno,
                "warehouse_code": r.warehouse_code,
                "project_code": r.project_code
            }
            listIds.append(singID)
        data = {
            "orders": listIds
        }
        back_data = {'code': 100, 'msg': '查询inbound order list成功', 'data': data}
        print("back_data==", back_data)
        return (back_data)

class GetInboundOrder(http.Controller):
    @http.route('/getInboundOrder', type='json', auth="user", cors="*", csrf=False)
    def getPacklist(self, **kw):
        # dingdan_h = 4900145711
        billno = kw.get('billno')
        # print("billno==", billno)
        inbound_order_by_billno = request.env['panexlogi.inbound.order'].sudo().search(
            [('billno', '=', billno)])  # 随便找个模型查询一条数据

        if not inbound_order_by_billno:
            back_data = {'code': 300, 'msg': 'inbound order不存在'}
            return (back_data)

        listIds = []
        for r in inbound_order_by_billno.inbound_order_product_ids:
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
            "billno": inbound_order_by_billno.billno,
            "date": inbound_order_by_billno.date,
            "waybillno": inbound_order_by_billno.waybillno,
            "products": listIds
        }
        back_data = {'code': 100, 'msg': '查询inbound order成功', 'data': data}
        print("back_data==", back_data)
        return (back_data)

    @http.route('/setInboundOperate', type='json', auth="user", cors="*", csrf=False)
    def setInboundOperate(self, **kw):
        inbound = kw.get('inbound')
        products = inbound["inbound_products"]  # kw.get('inbound_products')
        # print("inbound==", inbound)
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
            "date": inbound["date"],
            "order_billno": request.env['panexlogi.inbound.order'].sudo().search(
                [('billno', '=', inbound["order_billno"])]).id,
            "remark": inbound["remark"],
            "inbound_operate_product_ids": listIds
        }
        print("data==", data)
        id = request.env['panexlogi.inbound.operate'].sudo().create(data)
        back_data = {'code': 100, 'msg': '新增inbound成功', 'data': id.billno}
        return (back_data)
