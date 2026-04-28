# -*- coding: utf-8 -*-
{
    'name': 'Employee Profile Change Request',
    'version': '1.0',
    'category': 'Human Resources',
    'summary': 'Portal profile changes with HR approval workflow and email notifications',
    'author': 'Your Company',
    'depends': [
        'hr',
        'mail',
        'portal',
        'employee_self_service_portal',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/mail_template_data.xml',
        'views/email_templates.xml',
        'views/hr_profile_change_request_wizard_views.xml',
        'views/hr_profile_change_request_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}