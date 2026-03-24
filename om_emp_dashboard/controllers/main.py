# -*- coding: utf-8 -*-

from odoo import http, fields
from odoo.http import request
from datetime import datetime, timedelta
import pytz
import math
import calendar


class EmployeeDashboardController(http.Controller):

    def _get_week_type(self, day_date):
        """Return the week type (0 or 1) for a given date.

        Mirrors Odoo's resource.calendar.attendance.get_week_type().
        """
        return int(math.floor((day_date.toordinal() - 1) / 7) % 2)

    def _get_working_attendance_lines(self, resource_calendar, day_date):
        """Return attendance lines for a given date, respecting week_type
        and filtering out breaks and section headers."""
        if not resource_calendar:
            return []
        dow = str(day_date.weekday())
        lines = resource_calendar.attendance_ids.filtered(
            lambda a: a.dayofweek == dow
            and a.day_period != 'lunch'
            and not a.display_type
        )
        if resource_calendar.two_weeks_calendar:
            wt = str(self._get_week_type(day_date))
            lines = lines.filtered(lambda a: a.week_type == wt)
        return lines

    def _get_expected_hours_for_day(self, resource_calendar, day_date):
        """Return expected work hours for a given date based on schedule.

        Uses the resource.calendar.attendance lines filtered by dayofweek,
        week_type (for 2-week calendars), and excludes breaks/sections.
        Returns 0.0 for non-working days.
        """
        if not resource_calendar:
            return 0.0
        lines = self._get_working_attendance_lines(
            resource_calendar, day_date)
        total = 0.0
        for line in lines:
            total += (line.hour_to - line.hour_from)
        return total

    def _is_working_day(self, resource_calendar, day_date):
        """Check if a date is a scheduled working day."""
        if not resource_calendar:
            return day_date.weekday() < 5  # default Mon-Fri
        lines = self._get_working_attendance_lines(
            resource_calendar, day_date)
        return bool(lines)

    def _get_holidays_for_period(self, employee, period_start, period_end):
        """Fetch holidays from the employee's assigned holiday group.

        Returns a dict: {date_string: [{name, holiday_type, color}]}
        """
        holiday_map = {}
        if not employee or not employee.holiday_group_id:
            return holiday_map

        holidays = employee.holiday_group_id.holiday_ids.filtered(
            lambda h: h.date
            and h.date >= period_start and h.date <= period_end
        )

        for hol in holidays:
            date_str = hol.date.strftime('%Y-%m-%d')
            if date_str not in holiday_map:
                holiday_map[date_str] = []
            holiday_map[date_str].append({
                'name': hol.name,
                'holiday_type': hol.holiday_type,
                'color': hol.color or '#94a3b8',
            })

        return holiday_map

    @http.route('/om_emp_dashboard/get_dashboard_data', type='jsonrpc',
                auth='user')
    def get_dashboard_data(self, month=None, year=None):
        """Return dashboard data for the current user's employee."""
        user = request.env.user
        employee = request.env['hr.employee'].sudo().search(
            [('user_id', '=', user.id)], limit=1)

        # Resolve timezone using Odoo's employee fallback chain:
        # 1. Employee's resource calendar tz
        # 2. Employee's own tz
        # 3. User's tz setting
        # 4. Company's resource calendar tz
        # 5. UTC as final fallback
        tz_name = 'UTC'
        if employee:
            tz_name = employee._get_tz() or 'UTC'
        elif user.tz:
            tz_name = user.tz
        user_tz = pytz.timezone(tz_name)
        today = datetime.now(user_tz).date()

        if not month:
            month = today.month
        if not year:
            year = today.year

        month = int(month)
        year = int(year)

        first_day = datetime(year, month, 1).date()
        last_day = datetime(year, month,
                            calendar.monthrange(year, month)[1]).date()

        emp_id = employee.id if employee else 0
        resource_calendar = (employee.resource_calendar_id
                             if employee else False)
        joining_date = employee.joining_date if employee else None

        # Fetch holidays for this month
        holiday_map = self._get_holidays_for_period(
            employee, first_day, last_day)

        # Convert local month boundaries to UTC for correct querying
        month_start_local = user_tz.localize(
            datetime.combine(first_day, datetime.min.time()))
        month_end_local = user_tz.localize(
            datetime.combine(last_day, datetime.max.time()))
        month_start_utc = month_start_local.astimezone(pytz.utc)
        month_end_utc = month_end_local.astimezone(pytz.utc)

        # Attendance domain - always current employee (include open sessions)
        domain = [
            ('check_in', '>=', fields.Datetime.to_string(
                month_start_utc.replace(tzinfo=None))),
            ('check_in', '<=', fields.Datetime.to_string(
                month_end_utc.replace(tzinfo=None))),
            ('employee_id', '=', emp_id),
        ]

        attendances = request.env['hr.attendance'].sudo().search(domain)
        now_utc = datetime.utcnow()

        # Aggregate daily attendance data
        daily_data = {}
        for att in attendances:
            check_in_local = pytz.utc.localize(att.check_in).astimezone(
                user_tz)
            day_key = check_in_local.strftime('%Y-%m-%d')

            if day_key not in daily_data:
                daily_data[day_key] = {
                    'date': day_key,
                    'employee_id': att.employee_id.id,
                    'employee_name': att.employee_id.name,
                    'department': att.department_id.name or '',
                    'avatar_url': '/web/image/hr.employee/%d/avatar_128' % (
                        att.employee_id.id),
                    'first_check_in': check_in_local.strftime('%I:%M %p'),
                    'last_check_out': False,
                    'worked_hours': 0.0,
                    'check_in_raw': att.check_in.isoformat(),
                }
            entry = daily_data[day_key]
            if att.check_out:
                entry['worked_hours'] += att.worked_hours or 0.0
            else:
                # Open session: calculate live hours from check_in to now
                live_hours = (now_utc - att.check_in).total_seconds() / 3600.0
                entry['worked_hours'] += live_hours

            if att.check_out:
                check_out_local = pytz.utc.localize(
                    att.check_out).astimezone(user_tz)
                co_str = check_out_local.strftime('%I:%M %p')
                # Compare using raw UTC datetime to find latest check-out
                if (not entry.get('_last_co_raw') or
                        att.check_out > entry['_last_co_raw']):
                    entry['last_check_out'] = co_str
                    entry['_last_co_raw'] = att.check_out

        # Clean up internal tracking fields before building response
        for entry in daily_data.values():
            entry.pop('_last_co_raw', None)

        # Build calendar map with working day + holiday info
        calendar_data = {}
        current_date = first_day
        while current_date <= last_day:
            date_str = current_date.strftime('%Y-%m-%d')
            is_working = self._is_working_day(resource_calendar, current_date)
            expected = self._get_expected_hours_for_day(
                resource_calendar, current_date)
            entries = []
            if date_str in daily_data:
                entries.append(daily_data[date_str])

            # Holiday info for this date
            day_holidays = holiday_map.get(date_str, [])
            is_public_holiday = any(
                h['holiday_type'] == 'public' for h in day_holidays)

            # Determine day status
            before_joining = (joining_date
                              and current_date < joining_date)
            if before_joining:
                day_status = 'before_joining'
            elif is_public_holiday:
                day_status = 'public_holiday'
            elif not is_working:
                day_status = 'holiday'  # non-working day (weekend/off)
            elif entries:
                actual = sum(e['worked_hours'] for e in entries)
                if actual >= expected * 0.9:
                    day_status = 'present'
                elif actual >= expected * 0.5:
                    day_status = 'half_day'
                else:
                    day_status = 'short_day'
            elif current_date < today:
                day_status = 'absent'
            elif current_date == today:
                day_status = 'today_pending'
            else:
                day_status = 'upcoming'

            calendar_data[date_str] = {
                'entries': entries,
                'is_working_day': is_working,
                'expected_hours': round(expected, 1),
                'day_status': day_status,
                'holidays': day_holidays,
                'is_public_holiday': is_public_holiday,
            }
            current_date += timedelta(days=1)

        # KPI calculations using work schedule
        total_hours = 0.0
        for a in attendances:
            if a.check_out:
                total_hours += a.worked_hours or 0.0
            else:
                total_hours += (now_utc - a.check_in).total_seconds() / 3600.0

        # Count scheduled working days in the month (up to today)
        scheduled_working_days = 0
        days_present = 0
        days_absent = 0
        holidays_count = 0
        check_date = first_day
        limit_date = min(last_day, today)
        while check_date <= limit_date:
            # Skip days before employee joined
            if joining_date and check_date < joining_date:
                check_date += timedelta(days=1)
                continue
            date_str = check_date.strftime('%Y-%m-%d')
            day_holidays = holiday_map.get(date_str, [])
            is_public_hol = any(
                h['holiday_type'] == 'public' for h in day_holidays)

            if is_public_hol:
                holidays_count += 1
            elif self._is_working_day(resource_calendar, check_date):
                scheduled_working_days += 1
                if date_str in daily_data:
                    days_present += 1
                elif check_date < today:
                    days_absent += 1
            check_date += timedelta(days=1)

        # Today's attendance - convert local day boundaries to UTC
        today_start_local = user_tz.localize(
            datetime.combine(today, datetime.min.time()))
        today_end_local = user_tz.localize(
            datetime.combine(today, datetime.max.time()))
        today_start_utc = today_start_local.astimezone(pytz.utc)
        today_end_utc = today_end_local.astimezone(pytz.utc)

        today_domain = [
            ('check_in', '>=', fields.Datetime.to_string(
                today_start_utc.replace(tzinfo=None))),
            ('check_in', '<=', fields.Datetime.to_string(
                today_end_utc.replace(tzinfo=None))),
            ('employee_id', '=', emp_id),
        ]
        today_attendances = request.env['hr.attendance'].sudo().search(
            today_domain, order='check_in asc')

        today_check_in = False
        today_check_out = False
        today_worked = 0.0
        today_is_working = self._is_working_day(resource_calendar, today)
        today_expected = self._get_expected_hours_for_day(
            resource_calendar, today)

        # Check if today is a public holiday
        today_str = today.strftime('%Y-%m-%d')
        today_holidays = holiday_map.get(today_str, [])
        today_is_public_holiday = any(
            h['holiday_type'] == 'public' for h in today_holidays)

        if today_attendances:
            today_status = 'present'
            first = today_attendances[0]
            ci_local = pytz.utc.localize(first.check_in).astimezone(user_tz)
            today_check_in = ci_local.strftime('%I:%M %p')
            for ta in today_attendances:
                if ta.check_out:
                    today_worked += ta.worked_hours or 0.0
                    co_local = pytz.utc.localize(
                        ta.check_out).astimezone(user_tz)
                    today_check_out = co_local.strftime('%I:%M %p')
                else:
                    # Open session: calculate live hours
                    live_hours = (
                        now_utc - ta.check_in).total_seconds() / 3600.0
                    today_worked += live_hours
            # If the latest attendance has no check_out (employee is
            # currently checked in), clear the checkout time so the
            # tile shows '--:--' instead of a stale previous checkout.
            last = today_attendances[-1]
            if not last.check_out:
                today_check_out = False
        elif today_is_public_holiday:
            today_status = 'public_holiday'
        elif not today_is_working:
            today_status = 'day_off'
        else:
            today_status = 'absent'

        # Upcoming holidays from employee's holiday group
        upcoming_holidays = []
        if employee and employee.holiday_group_id:
            future_holidays = employee.holiday_group_id.holiday_ids.filtered(
                lambda h: h.date and h.date >= today
            ).sorted('date')
            for hol in future_holidays[:10]:
                days_until = (hol.date - today).days
                upcoming_holidays.append({
                    'name': hol.name,
                    'date': hol.date.strftime('%d %b %Y'),
                    'date_short': hol.date.strftime('%d %b'),
                    'day_name': hol.date.strftime('%A'),
                    'holiday_type': hol.holiday_type,
                    'color': hol.color or '#94a3b8',
                    'days_until': days_until,
                })

        # Upcoming celebrations (birthdays + work anniversaries, next 30 days)
        upcoming_celebrations = []
        end_date = today + timedelta(days=30)

        # Helper to get this year's occurrence of a recurring date
        def _get_upcoming_date(orig_date):
            try:
                this_year = orig_date.replace(year=today.year)
            except ValueError:
                this_year = orig_date.replace(year=today.year, day=28)
            if this_year < today:
                try:
                    this_year = orig_date.replace(year=today.year + 1)
                except ValueError:
                    this_year = orig_date.replace(
                        year=today.year + 1, day=28)
            return this_year

        all_employees = request.env['hr.employee'].sudo().search(
            ['|', ('birthday', '!=', False),
             ('joining_date', '!=', False)])

        for emp in all_employees:
            base_info = {
                'name': emp.name,
                'avatar_url': (
                    '/web/image/hr.employee/%d/avatar_128' % emp.id),
                'department': emp.department_id.name or '',
                'job_title': emp.job_title or '',
            }
            # Birthday
            if emp.birthday:
                bday_date = _get_upcoming_date(emp.birthday)
                if today <= bday_date <= end_date:
                    upcoming_celebrations.append({
                        **base_info,
                        'date_short': bday_date.strftime('%d %b'),
                        'day_name': bday_date.strftime('%A'),
                        'days_until': (bday_date - today).days,
                        'type': 'birthday',
                        'years': 0,
                    })
            # Work anniversary
            if emp.joining_date and emp.joining_date < today:
                anniv_date = _get_upcoming_date(emp.joining_date)
                years = anniv_date.year - emp.joining_date.year
                if years > 0 and today <= anniv_date <= end_date:
                    upcoming_celebrations.append({
                        **base_info,
                        'date_short': anniv_date.strftime('%d %b'),
                        'day_name': anniv_date.strftime('%A'),
                        'days_until': (anniv_date - today).days,
                        'type': 'anniversary',
                        'years': years,
                    })

        upcoming_celebrations.sort(key=lambda x: x['days_until'])

        return {
            'calendar_data': calendar_data,
            'month': month,
            'year': year,
            'month_name': calendar.month_name[month],
            'today': today.strftime('%Y-%m-%d'),
            'kpi': {
                'total_hours': round(total_hours, 1),
                'working_days': days_present,
                'scheduled_days': scheduled_working_days,
                'days_absent': days_absent,
                'holidays_count': holidays_count,
                'today_status': today_status,
                'today_check_in': today_check_in or '--:--',
                'today_check_out': today_check_out or '--:--',
                'today_worked': round(today_worked, 1),
                'today_expected': round(today_expected, 1),
                'today_is_working': today_is_working,
            },
            'upcoming_holidays': upcoming_holidays,
            'upcoming_birthdays': upcoming_celebrations,
            'current_employee_name': employee.name if employee else '',
        }
