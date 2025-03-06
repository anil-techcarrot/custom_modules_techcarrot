# -*- coding: utf-8 -*-
{
    'name': 'Techcarret Invoice Templates',
    'summary': "Techcarret Invoice Templates",
    'description': "Techcarret Invoice Templates ",

    'author': 'Ifensys.',

    'category': 'Account',
    'version': '18.0.0.1.0',
    'depends': ['sale_management', 'stock', 'sale_renting', 'account', 'sale'],

    'data': [
        'reports/invoice_report_template.xml',
        'reports/invoice_ir_actions.xml',
        'views/res_bank_view.xml',
        'views/sale_order_view.xml',
    ],

    # 'license': "AGPL-1",

    'auto_install': False,
    'installable': True,


    'pre_init_hook': 'pre_init_check',
}
