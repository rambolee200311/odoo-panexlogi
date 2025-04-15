# -*- coding: utf-8 -*-
{
    'name': "panexLogi",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "PanexWD BV",
    'website': "https://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/16.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'stock', 'sale', 'fleet', 'portal', 'payment', 'resource', 'web', 'spreadsheet'],

    # always loaded
    'data': [
        'security/panexlogi_security.xml',
        #'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
        'views/waybill.xml',
        'views/waybill_arrivnotice.xml',
        'views/waybill_commeinvoice.xml',
        'views/waybill_packList.xml',
        'views/waybill_shipinvoice.xml',
        'views/waybill_clearinvoice.xml',
        'views/waybill_custduty.xml',
        'views/waybill_cargoRelease.xml',
        'views/waybill_cargoRelease_line.xml',
        'views/waybill_details.xml',
        'views/waybill_batch_edit.xml',
        'views/Panex_partner.xml',
        'views/sender.xml',
        'views/receiver.xml',
        'views/project.xml',
        'views/fitem.xml',
        'views/cartage.xml',
        'views/cartage_tag_views.xml',
        'views/cartage_offer_views.xml',
        'views/cartage_trail_views.xml',
        'views/importpayapp.xml',
        'views/cartagepayapp.xml',
        'views/settlebill.xml',
        'views/settlebill_clearance.xml',
        'views/settlebill_handling.xml',
        'views/settlebill_inbound.xml',
        'views/settlebill_outbound.xml',
        'views/settlebill_delivery.xml',
        'views/loadingcondition.xml',
        'views/inbound_order.xml',
        'views/inbound_operate.xml',
        'views/inbound_order_product_scan.xml',
        'views/outbound_order.xml',
        'views/outbound_operate.xml',
        'views/DemoTodo.xml',
        'views/packagetype.xml',
        'views/delivery_request.xml',
        'views/delivery_detail.xml',
        'views/delivery_quote.xml',
        'views/delivery_invoice.xml',
        'views/DemoStockPicking.xml',
        'views/DemoToDoReport.xml',
        'views/country.xml',
        'views/deliverytype.xml',
        'views/terminal.xml',
        'views/transportcontract.xml',
        'views/transportorder.xml',
        'views/transportinvoice.xml',
        'views/transport_order_extended.xml',
        'views/payment_method.xml',
        'views/period.xml',
        'views/payment.xml',
        'views/warehouse_invoice.xml',
        'views/settle_shipping.xml',
        'views/settle_clearance.xml',
        'views/clearance_type.xml',
        'views/delivery_order.xml',
        'views/excel_template.xml',
        'views/address.xml',
        'data/ir_cron_data.xml',
        'views/sequence.xml',
        'report/report.xml',
        'views/menus.xml',
        'views/template_panexlogi.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml', 'data/fitem.xml', 'data/productname.xml',
    ],
    'assets': {
        'web.assets_backend': [
             # 'static/src/js/samplecollection_barcode_handler.js',
             # 'static/src/xml/*.xml',
             # 'static/src/xml/samplecollection_barcode_handler.xml'
            #'static/src/scss/styles_panexlogi.scss',
        ],
    },

}
