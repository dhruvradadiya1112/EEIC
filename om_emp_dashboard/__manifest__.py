# -*- coding: utf-8 -*-
{
    'name': 'Employee Dashboard',
    'version': '19.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Employee Dashboard with Calendar View for Work Hours',
    'description': """
Employee Dashboard
==================
A custom dashboard module that provides:

* Interactive calendar view of daily work hours per employee
* KPI cards for today's status, check-in/out, hours, working days
* Holiday management with calendar integration
* Upcoming celebrations (birthdays and work anniversaries)
* Security group for holiday management access control
""",
    'author': 'OdooMatrix',
    'company': 'OdooMatrix',
    'website': 'https://odoomatrix.com',
    'depends': ['hr_attendance'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/om_emp_dashboard_views.xml',
        'views/employee_holiday_views.xml',
    ],
    'images': [
        'static/description/banner.png',
        'static/description/dashboard_full.png',
        'static/description/holiday_group_form.png',
        'static/description/employee_form_fields.png',
    ],
    'assets': {
        'web.assets_backend': [
            'om_emp_dashboard/static/src/js/om_emp_dashboard.js',
            'om_emp_dashboard/static/src/xml/om_emp_dashboard.xml',
            'om_emp_dashboard/static/src/scss/om_emp_dashboard.scss',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
