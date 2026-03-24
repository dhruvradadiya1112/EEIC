from odoo import http
from odoo.http import request
from datetime import datetime
import calendar


class ServiceDashboardController(http.Controller):

    @http.route('/service_dashboard/get_data', type='json', auth='user')
    def get_data(self, month, year):

        month = int(month)
        year = int(year)

        start_date = datetime(year, month, 1).date()

        if month == 12:
            end_date = datetime(year + 1, 1, 1).date()
        else:
            end_date = datetime(year, month + 1, 1).date()

        # ✅ FILTER BY DATE + STATE for Service Requests
        services = request.env['service.request'].sudo().search([
            ('scheduled_date', '>=', start_date),
            ('scheduled_date', '<', end_date),
            ('state', 'in', ['assigned', 'in_progress']),
        ])
        
        # ✅ Get Fleet History data
        fleet_history = request.env['fleet.history'].sudo().search([
            ('scheduled_date', '>=', start_date),
            ('scheduled_date', '<', end_date),
            ('service_request_id.state', 'in', ['assigned', 'in_progress']),
        ])
        
        users = request.env['res.users'].sudo().search([
            ('is_service_user', '=', True)
        ])
        
        # ✅ Get all fleets
        all_fleets = request.env['fleet.managment'].sudo().search([])

        calendar_data = {}

        # Process Service Requests
        for s in services:
            if not s.scheduled_date:
                continue

            date_str = s.scheduled_date.strftime('%Y-%m-%d')

            if date_str not in calendar_data:
                calendar_data[date_str] = []

            calendar_data[date_str].append({
                'id': s.id,
                'name': s.name or '',
                'user': s.user_id.name or '',
                'user_id': s.user_id.id,
                'date': str(s.scheduled_date),
                'state': s.state,
                'type': 'service',
                'fleet_id': s.fleet_id.id if s.fleet_id else False,
                'fleet_name': s.fleet_id.display_name if s.fleet_id else '',
            })

        # Process Fleet History
        for fh in fleet_history:
            if not fh.scheduled_date:
                continue

            date_str = fh.scheduled_date.strftime('%Y-%m-%d')

            if date_str not in calendar_data:
                calendar_data[date_str] = []

            calendar_data[date_str].append({
                'id': fh.id,
                'name': fh.name or f"Fleet Assignment",
                'user': fh.user_id.name or '',
                'user_id': fh.user_id.id,
                'date': str(fh.scheduled_date),
                'type': 'fleet',
                'fleet_id': fh.fleet_id.id,
                'fleet_name': fh.fleet_id.display_name,
                'service_request_id': fh.service_request_id.id,
                'service_name': fh.service_request_id.name if fh.service_request_id else '',
            })

        employees = [{
            'id': u.id,
            'name': u.name
        } for u in users]
        
        # ✅ Get all fleets with display name
        fleets = [{
            'id': f.id,
            'name': f.name,
            'number': f.number,
            'display_name': f.display_name,
        } for f in all_fleets]

        return {
            'calendar_data': calendar_data,
            'employees': employees,
            'fleets': fleets,  # ✅ Add fleets to response
            'month_name': calendar.month_name[month],
            'today': datetime.today().strftime('%Y-%m-%d'),
        }