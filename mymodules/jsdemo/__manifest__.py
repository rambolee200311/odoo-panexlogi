# -*- coding: utf-8 -*-
{
    'name': "jsdemo",

    'summary': "Short (1 phrase/line) summary of the module's purpose",

    'description': """
Long description of module's purpose
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',
    # any module necessary for this one to work correctly
    'depends': ['web', 'base', 'stock', 'sale', 'fleet', 'portal', 'payment', 'resource'],
    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/delivery.xml',
        'views/menu.xml',
        'views/deliverylinewizard.xml',
        'views/trucking.xml',
    ],
    'assets': {
        'web.assets_backend': [
            #'https://cdn.jsdelivr.net/npm/x-data-spreadsheet@1.1.4/dist/xspreadsheet.css',
            #'https://cdn.jsdelivr.net/npm/x-data-spreadsheet@1.1.4/dist/xspreadsheet.js',
            'jsdemo/static/src/css/truckingline.css',
            'jsdemo/static/src/css/spreadsheet.css',
            'jsdemo/static/src/js/list_view.js',
        ]},
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
