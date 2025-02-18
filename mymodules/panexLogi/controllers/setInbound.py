from odoo import http, fields
from odoo.http import request


# 逐行更新入库订单明细
class setInboundProduct(http.Controller):
    @http.route('/setInboundProduct', type='json', auth="user", cors="*", csrf=False)
    def setInboundProduct(self, **kw):
        did = kw.get('did')

        be_del = kw.get('be_del')
        if not be_del:
            be_del = False
        ori_pda_id = kw.get('ori_pda_id')
        if not ori_pda_id:
            ori_pda_id = ''

        if ori_pda_id != '':
            product_scan = request.env['panexlogi.inbound.order.products.scan'].sudo().search(
                [('pda_id', '=', ori_pda_id)])
            if not product_scan:
                back_data = {'code': 300, 'msg': 'pda_id Not Exist'}
                return back_data

        inbound_order_products = request.env['panexlogi.inbound.order.products'].sudo().search([('id', '=', did)])
        if not inbound_order_products:
            back_data = {'code': 300, 'msg': 'inbound order products不存在'}
            return (back_data)
        else:
            if ori_pda_id != '' and be_del:
                request.env['panexlogi.inbound.order.products.scan'].sudo().search(
                    [('pda_id', '=', ori_pda_id)]).write({'be_del': be_del})

            request.env['panexlogi.inbound.order.products.scan'].sudo().create({
                'inbound_order_products_id': did,
                'warehouse_id': kw.get('warehouse_id'),
                'location_id': kw.get('location_id'),
                'pda_id': kw.get('pda_id'),
                'product_id': kw.get('product_id'),
                'batch': kw.get('batch'),
                'pcs': kw.get('pcs'),
                'pallets': kw.get('pallets'),
                'cntrno': kw.get('cntrno'),
                'palletdno': kw.get('palletdno'),
                'sncode': kw.get('sncode'),
                'be_del': be_del,
                'ori_pda_id': ori_pda_id,
            })  # 新增inbound order products scan

            inbound_order_products.write({
                'state': 'in-Operation',
                'total_pallets': inbound_order_products.total_pallets + kw.get('pallets'),
                'total_pcs': inbound_order_products.total_pcs + kw.get('pcs'),
            })  # 更新inbound order products

            back_data = {'code': 100, 'msg': '更新inbound order products成功'}
            return back_data


# 获取入库订单操作明细
class getInboundProduct(http.Controller):
    @http.route('/getInboundProduct', type='json', auth="user", cors="*", csrf=False)
    def getInboundProduct(self, **kw):
        domain = []
        # domain.append('&')
        # domain.append((1, '=', 1))
        # order id
        id = kw.get('id')
        if id:
            inboundorders = request.env['panexlogi.inbound.order.products'].sudo().search([('inboundorderid', '=', id)])
            if inboundorders:
                # domain.append('&')
                j = len(inboundorders)
                if j > 1:
                    for i in range(1, j):
                        domain.append('|')
                # domain.append((1, '=', 0))
                for r in inboundorders:
                    domain.append(('inbound_order_products_id', '=', r.id))

        # order products id
        did = kw.get('did')
        if did:
            # domain.append('&')
            # domain.append((1, '=', 1))
            domain.append(('inbound_order_products_id', '=', did))
        # order products product_id
        product_id = kw.get('product_id')
        if product_id:
            domain.append(('product_id', '=', product_id))
        # order products pda_id
        pda_id = kw.get('pda_id')
        if pda_id:
            domain.append(('pda_id', '=', pda_id))
        # order products cntrno
        cntrno = kw.get('cntrno')
        if cntrno:
            domain.append(('cntrno', '=', cntrno))
        palletdno = kw.get('palletdno')
        if palletdno:
            domain.append(('palletdno', '=', palletdno))
        batch = kw.get('batch')
        if batch:
            domain.append(('batch', '=', batch))

        domain.append(('be_del', '=', False))

        inbound_order_products_scan = request.env['panexlogi.inbound.order.products.scan'].sudo().search(domain)
        if not inbound_order_products_scan:
            back_data = {'code': 300, 'msg': 'inbound order product scan 不存在'}
            return (back_data)

        listIds = []
        for r in inbound_order_products_scan:
            singID = {
                "did": r.id,
                "inbound_order_products_id": r.inbound_order_products_id.id,
                "warehouse_id": r.warehouse_id.id,
                "location_id": r.location_id.id,
                "pda_id": r.pda_id,
                "product_id": r.product_id.id,
                "product_name": r.product_id.name,
                "product_barcode": r.product_id.barcode,
                "batch": r.batch,
                "cntrno": r.cntrno,
                "pcs": r.pcs,
                "pallets": r.pallets,
                "palletdno": r.palletdno,
                "sncode": r.sncode,
            }
            listIds.append(singID)
        data = {"productscan": listIds}
        back_data = {'code': 100, 'msg': '查询inbound order product scan成功', 'data': data}
        return back_data


# 新增入库操作
class setInboundOperate(http.Controller):
    @http.route('/setInboundOperate', type='json', auth="user", cors="*", csrf=False)
    def setInboundOperate(self, **kw):
        inbound = kw.get('inbound')
        # products = inbound["inbound_products"]  # kw.get('inbound_products')
        # print("inbound==", inbound)
        # print("products==", products)
        # stockPicks=open("stockPicks.json", "r")
        # listStockPicks=json.load(stockPicks)
        domain = []
        inboundorderid = inbound["id"]
        if not inboundorderid:
            back_data = {'code': 300, 'msg': 'inbound order id 不能为空'}
            return back_data

        inboundorder = request.env['panexlogi.inbound.order'].sudo().search([('id', '=', inboundorderid)])
        if not inboundorder:
            back_data = {'code': 300, 'msg': 'inbound order 不存在'}
            return back_data
        else:
            inboundorders = request.env['panexlogi.inbound.order.products'].sudo().search(
                [('inboundorderid', '=', inboundorderid)])
            if inboundorders:
                # domain.append('&')
                j = len(inboundorders)
                if j > 1:
                    for i in range(1, j):
                        domain.append('|')
                for r in inboundorders:
                    domain.append(('inbound_order_products_id', '=', r.id))

        domain.append(('be_del', '=', False))

        inbound_order_products_scan = request.env['panexlogi.inbound.order.products.scan'].sudo().search(domain)
        if not inbound_order_products_scan:
            back_data = {'code': 300, 'msg': 'inbound order product scan 不存在'}
            return (back_data)

        listIds = []
        for r in inbound_order_products_scan:
            oder_billno = 0
            if r["inbound_order_products_id"]:
                oder_billno = r["inbound_order_products_id"].id
            product_id = 0
            if r["product_id"]:
                product_id = r["product_id"].id
            warehouse_id = 0
            if r["warehouse_id"]:
                warehouse_id = r["warehouse_id"].id
            location_id = 0
            if r["location_id"]:
                location_id = r["location_id"].id
            pcs = 0
            if r["pcs"]:
                pcs = r["pcs"]
            pallets = 0
            if r["pallets"]:
                pallets = r["pallets"]
            batch = ""
            if r["batch"]:
                batch = r["batch"]
            cntrno = ""
            if r["cntrno"]:
                cntrno = r["cntrno"]
            palletdno = ""
            if r["palletdno"]:
                palletdno = r["palletdno"]
            sncode = ""
            if r["sncode"]:
                sncode = r["sncode"]

            singID = (0, 0, {
                "oder_billno": oder_billno,
                "product_id": product_id,
                "warehouse_id": warehouse_id,
                "location_id": location_id,
                "pcs": pcs,
                "pallets": pallets,
                "batch": batch,
                "cntrno": cntrno,
                "palletdno": palletdno,
                "sncode": sncode,
            })
            listIds.append(singID)

        remark = ""
        if inbound["remark"]:
            remark = inbound["remark"]
        data = {
            "date": inbound["date"],
            "pda_id": inbound["pda_id"],
            "order_billno": request.env['panexlogi.inbound.order'].sudo().search([('id', '=', inboundorderid)]).id,
            "remark": remark,
            "inbound_operate_product_ids": listIds
        }

        print("data==", data)

        request.env['panexlogi.inbound.order'].sudo().search([('id', '=', inboundorderid)]).write({'state': 'done'})

        new_inboundorderid = request.env['panexlogi.inbound.operate'].sudo().create(data)
        back_data = {'code': 100, 'msg': '新增inbound operate成功', 'data': new_inboundorderid.billno}
        return back_data
