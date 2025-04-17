# -*- coding: utf-8 -*-
{
    'name': 'Techcarret Rental Orders',
    'summary': "Techcarret Rental Orders",
    'description': "Techcarret Rental Orders",
    'author': 'Ifensys',
    'category': 'Sales',
    'version': '18.1',
    'depends': ['product', 'sale_management', 'sale', 'stock', 'sale_renting', 'hr', 'hr_work_entry', 'account', 'analytic', 'sale_subscription', 'sale_stock_renting', 'techcarrot_employee', 'techcarrot_contacts'],
    'data': [
        'security/ir.model.access.csv',
        'security/rental_security.xml',
        'views/sequence_view.xml',
        'views/tec_project_type_views.xml',
        'views/res_config_settings_views.xml',
        'views/rental_order_view.xml',
        'views/employee_view.xml',
        'views/import_attendance_view.xml',
        'views/cron_view.xml',
        'views/menu_view.xml'
    ],
    'auto_install': False,
    'installable': True,
}
