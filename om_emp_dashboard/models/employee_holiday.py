# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class EmployeeHolidayGroup(models.Model):
    _name = 'employee.holiday.group'
    _description = 'Employee Holiday Group'
    _order = 'name'
    _rec_name = 'name'

    name = fields.Char(
        string="Group Name", required=True,
        help="e.g. India 2026 Holidays, US 2026 Holidays")
    description = fields.Text(string="Description")
    company_id = fields.Many2one(
        'res.company', string="Company",
        default=lambda self: self.env.company)
    holiday_ids = fields.One2many(
        'employee.holiday', 'group_id',
        string="Holidays")
    holiday_count = fields.Integer(
        string="Holiday Count",
        compute='_compute_holiday_count')
    employee_ids = fields.One2many(
        'hr.employee', 'holiday_group_id',
        string="Employees")
    employee_count = fields.Integer(
        string="Employee Count",
        compute='_compute_employee_count')

    @api.depends('holiday_ids')
    def _compute_holiday_count(self):
        for rec in self:
            rec.holiday_count = len(rec.holiday_ids)

    @api.depends('employee_ids')
    def _compute_employee_count(self):
        for rec in self:
            rec.employee_count = len(rec.employee_ids)


class EmployeeHoliday(models.Model):
    _name = 'employee.holiday'
    _description = 'Employee Holiday'
    _order = 'date'
    _rec_name = 'name'

    group_id = fields.Many2one(
        'employee.holiday.group', string="Holiday Group",
        ondelete='cascade', index=True)
    name = fields.Char(
        string="Holiday Name", required=True,
        help="Name of the holiday, e.g. Christmas, Diwali")
    date = fields.Date(
        string="Date", required=True, index=True)
    holiday_type = fields.Selection([
        ('public', 'Public Holiday'),
        ('company', 'Company Holiday'),
        ('optional', 'Optional Holiday'),
        ('restricted', 'Restricted Holiday'),
    ], string="Type", default='public', required=True)
    color = fields.Char(
        string="Color", default='#94a3b8',
        help="Color to display in calendar")
    description = fields.Text(string="Description")



class HrEmployeeInherit(models.Model):
    _inherit = 'hr.employee'

    holiday_group_id = fields.Many2one(
        'employee.holiday.group',
        string="Holiday Group",
        help="Assign a holiday group to this employee")
    joining_date = fields.Date(
        string="Joining Date",
        tracking=True,
        help="Date when the employee joined the company")
