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
        'views/service_dashboard.xml',
        'data/sequence.xml',
        'views/res_users_views.xml',
        #'views/service_calendar.xml'
        
    ],
    
     'assets': {
        'web.assets_backend': [
            'service_request_management/static/src/css/dashboard.css',
            'service_request_management/static/src/js/om_emp_dashboard.js',
            'service_request_management/static/src/xml/om_emp_dashboard.xml',
            #'service_request_management/static/src/scss/om_emp_dashboard.scss',
        ],
    },
     
     
     
     
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}