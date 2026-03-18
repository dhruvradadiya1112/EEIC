{
    'name': 'Service Request Management',
    'version': '1.0',
    'category': 'Sales',
    'summary': 'Manage service requests and timesheets from sales orders',
    'description': """
        This module allows you to:
        - Create service requests from sales orders
        - Assign employees to service requests
        - Track timesheets for service work
        - Create invoices from timesheets
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['sale', 'hr', 'account'],
    'data': [
        'security/ir.model.access.csv',
         'security/security.xml',
        'views/service_request_views.xml',
        'views/sale_order_views.xml',
        'views/fleet_manag_views.xml',
        'data/sequence.xml'
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}