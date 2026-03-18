{
    'name': 'AI Conversation Analyzer',
    'version': '1.0',
    'summary': 'Analyze client conversations using AI',
    'depends': ['crm', 'calendar'],
    'data': [
        'security/ir.model.access.csv',
        'views/crm_lead_view.xml',
    ],
    'installable': True,
    'application': False,
}