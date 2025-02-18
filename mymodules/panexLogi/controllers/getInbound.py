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

        domain.append(('state', '!=', 'done'))

        inbound_orders = request.env['panexlogi.inbound.order'].sudo().search(domain)

        if not inbound_orders:
            back_data = {'code': 300, 'msg': 'inbound order list不存在'}
            return (back_data)

        listIds = []
        for r in inbound_orders:
            singID = {
                "id": r.id,
                "billno": r.billno,
                "date": r.date,
                "waybillno": r.waybillno,
                "warehouse_id": r.warehouse.id,
                "warehouse_code": r.warehouse_code,
                "project_id": r.project.id,
                "project_code": r.project_code
            }
            listIds.append(singID)
        data = {
            "orders": listIds
        }
        back_data = {'code': 100, 'msg': '查询inbound order list成功', 'data': data}
        print("back_data==", back_data)
        return back_data


class GetInboundOrder(http.Controller):
    @http.route('/getInboundOrder', type='json', auth="user", cors="*", csrf=False)
    def getPacklist(self, **kw):
        domain = []
        # dingdan_h = 4900145711
        id = kw.get('id')
        # print("id==", id)
        if id:
            domain.append(('id', '=', id))
        billno = kw.get('billno')
        # print("billno==", billno)
        if billno:
            domain.append(('billno', '=', billno))

        domain.append(('state', '!=', 'done'))

        inbound_order_by_billno = request.env['panexlogi.inbound.order'].sudo().search(domain)  # 随便找个模型查询一条数据

        if not inbound_order_by_billno:
            back_data = {'code': 300, 'msg': 'inbound order不存在'}
            return (back_data)

        listIds = []
        for r in inbound_order_by_billno.inbound_order_product_ids:
            singID = {
                "did": r.id,
                "product_id": r.product_id.id,
                "product_name": r.product_id.name,
                "product_barcode": r.product_id.barcode,
                "batch": r.batch,
                "cntrno": r.cntrno,
                "pcs": r.pcs,
                "pallets": r.pallets,
                "palletdno": r.palletdno,
                "total_pallets": r.total_pallets,
                "total_pcs": r.total_pcs,
            }
            listIds.append(singID)
        data = {
            "id": inbound_order_by_billno.id,
            "billno": inbound_order_by_billno.billno,
            "date": inbound_order_by_billno.date,
            "waybillno": inbound_order_by_billno.waybillno,
            "warehouse_id": inbound_order_by_billno.warehouse.id,
            "warehouse_code": inbound_order_by_billno.warehouse_code,
            "project_id": inbound_order_by_billno.project.id,
            "project_code": inbound_order_by_billno.project_code,
            "products": listIds,
            "operate_type": "ABCD操作类别"
        }
        back_data = {'code': 100, 'msg': '查询inbound order成功', 'data': data}
        print("back_data==", back_data)
        return (back_data)


