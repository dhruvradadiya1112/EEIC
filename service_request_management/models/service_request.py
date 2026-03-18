from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError


class ServiceRequest(models.Model):
    _name = 'service.request'
    _description = 'Service Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    name = fields.Char(string='Reference', default='New', readonly=True, tracking=True)
    partner_id = fields.Many2one('res.partner', string="Customer", required=True, tracking=True)
    sale_order_id = fields.Many2one('sale.order', string="Sales Order", tracking=True)
    user_id = fields.Many2one('res.users', string="Assigned To", tracking=True)
    
    description = fields.Text(string="Description/Instructions")
    scheduled_date = fields.Date(string="Scheduled Date")
    deadline_date = fields.Date(string="Deadline")
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('assigned', 'Assigned'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
        ('approved', 'approved'),
        ('cancelled', 'Cancelled'),
    ], default='draft', string='Status', tracking=True)

    timesheet_ids = fields.One2many('service.timesheet', 'request_id', string="Timesheets")
    
    total_hours = fields.Float(string="Total Hours", compute='_compute_totals', store=True)
    total_amount = fields.Float(string="Total Amount", compute='_compute_totals', store=True)
    
    company_id = fields.Many2one('res.company', string='Company', 
                                  default=lambda self: self.env.company)
    
    
    invoice_id = fields.Many2one('account.move', string="Bill", readonly=True)
    invoice_count = fields.Integer(compute="_compute_invoice_count")
    
    
    
    
    is_fleet_required = fields.Boolean(string="Fleet Required")
    
    
    fleet_id = fields.Many2one('fleet.managment', string="Fleet", tracking=True)
    
    

    from_datetime = fields.Datetime(string="From Date & Time")
    to_datetime = fields.Datetime(string="To Date & Time")
    
    duration_hours = fields.Float(string="Duration (Hours)", compute="_compute_duration", store=True)
    
    
    
    @api.constrains('is_fleet_required', 'fleet_id', 'from_datetime', 'to_datetime')
    def _check_fleet_fields(self):
        for rec in self:
            if rec.is_fleet_required:
                if not rec.fleet_id:
                    raise ValidationError("Please select a Fleet.")
                if not rec.from_datetime or not rec.to_datetime:
                    raise ValidationError("Please set From and To Date & Time.")
            
            
    

    @api.depends('from_datetime', 'to_datetime')
    def _compute_duration(self):
        for rec in self:
            if rec.from_datetime and rec.to_datetime:
                diff = rec.to_datetime - rec.from_datetime
                rec.duration_hours = diff.total_seconds() / 3600.0
            else:
                rec.duration_hours = 0.0
                
    def _check_datetime(self):
        for rec in self:
            if rec.from_datetime and rec.to_datetime:
                if rec.to_datetime <= rec.from_datetime:
                    raise ValidationError("End time must be greater than start time.")
            
            
            
            
    @api.constrains('fleet_id', 'from_datetime', 'to_datetime')
    def _check_fleet_availability(self):
        for rec in self:
            if rec.fleet_id and rec.from_datetime and rec.to_datetime:
                domain = [
                    ('fleet_id', '=', rec.fleet_id.id),
                    ('id', '!=', rec.id),
                    ('from_datetime', '<', rec.to_datetime),
                    ('to_datetime', '>', rec.from_datetime),
                ]
                if self.search_count(domain):
                    raise ValidationError("This fleet is already assigned in this time range.")
            
            
                              








    def _compute_invoice_count(self):
        for rec in self:
            rec.invoice_count = 1 if rec.invoice_id else 0
        
        
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('service.request') or 'New'
        return super().create(vals_list)
    
    
    

    @api.depends('timesheet_ids.hours', 'timesheet_ids.amount')
    def _compute_totals(self):
        for rec in self:
            rec.total_hours = sum(rec.timesheet_ids.mapped('hours'))
            rec.total_amount = sum(rec.timesheet_ids.mapped('amount'))

    
    def action_assigned(self):
        
        if not self.user_id:
            raise UserError("No Any Assigned found.")
        
        if not self.scheduled_date:
            raise UserError("Scheduled Date Is Required.")
        
        if not self.deadline_date:
            raise UserError("Deadline Date Is Required.")
        
        
        
        self.state = 'assigned'
    
        for rec in self:
            if rec.fleet_id and rec.from_datetime and rec.to_datetime:
                self.env['fleet.history'].create({
                    'fleet_id': rec.fleet_id.id,
                    'service_request_id': rec.id,
                    'name': rec.name,
                    'user_id': rec.user_id.id,
                    'from_datetime': rec.from_datetime,
                    'to_datetime': rec.to_datetime,
                    'duration': rec.duration_hours,
                })
        
        
    def action_start(self):
        """Start working on the service request"""
        self.state = 'in_progress'

    def action_done(self):
        """Mark service request as done"""
        self.state = 'done'

    def action_cancel(self):
        """Cancel service request"""
        self.state = 'cancelled'

    def action_create_invoice(self):
        if not self.timesheet_ids:
            raise UserError("No timesheets found to bill.")
        
        if self.state != 'done':
            raise UserError("Service request must be 'Done' before billing.")
    
        if self.invoice_id:
            raise UserError("Bill already created.")
    
        invoice_lines = []
    
        for timesheet in self.timesheet_ids:
            role_dict = dict(self.env['service.timesheet']._fields['role'].selection)
            description = f"{role_dict.get(timesheet.role)} - {getattr(timesheet, 'name', 'Work')}"
            
            if timesheet.description:
                description += f"\n{timesheet.description}"
    
            invoice_lines.append((0, 0, {
                'name': description,
                'quantity': timesheet.hours,
                'price_unit': timesheet.rate,
            }))
    
        bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.user_id.id,
            'invoice_origin': self.name,
            'invoice_line_ids': invoice_lines,
        })
    
        # ✅ Link bill to service request
        self.invoice_id = bill.id
    
        return {
            'type': 'ir.actions.act_window',
            'name': 'Created Bill',
            'res_model': 'account.move',
            'res_id': bill.id,
            'view_mode': 'form',
            'target': 'current',
        }

        
    def action_view_invoice(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Bill',
            'res_model': 'account.move',
            'res_id': self.invoice_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    




class Fleetmanagment(models.Model):
    _name = 'fleet.managment'
    _description = 'Fleet Management'

    name = fields.Char(string='Name', required=True)
    number = fields.Char(string='Number', required=True)

    # ✅ Important for Odoo 17+
    display_name = fields.Char(compute="_compute_display_name", store=True)
    
    
    history_ids = fields.One2many('fleet.history', 'fleet_id', string="History")

    @api.depends('name', 'number')
    def _compute_display_name(self):
        for rec in self:
            if rec.number:
                rec.display_name = f"{rec.name} ({rec.number})"
            else:
                rec.display_name = rec.name or ''

    # Optional (for compatibility)
    def name_get(self):
        return [(rec.id, rec.display_name) for rec in self]

    # ✅ Search by name OR number
    def _name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        domain = ['|', ('name', operator, name), ('number', operator, name)]
        return self.search(domain + args, limit=limit).name_get()
    
    
class FleetHistory(models.Model):
    _name = 'fleet.history'
    _description = 'Fleet Assignment History'
    _order = 'from_datetime desc'

    fleet_id = fields.Many2one('fleet.managment', string="Fleet", required=True)
    service_request_id = fields.Many2one('service.request', string="Service Request")

    name = fields.Char(string="Reference")
    user_id = fields.Many2one('res.users', string="Assigned User")

    from_datetime = fields.Datetime(string="From")
    to_datetime = fields.Datetime(string="To")

    duration = fields.Float(string="Duration (Hours)")
    
    
    



class FleetAvailabilityWizard(models.TransientModel):
    _name = 'fleet.availability.wizard'
    _description = 'Fleet Availability'

    fleet_id = fields.Many2one('fleet.managment', string="Fleet", required=True)
    
    
    

    def action_view_calendar(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Fleet Schedule',
            'res_model': 'service.request',
            'view_mode': 'calendar',
            'views': [(self.env.ref('service_request_management.view_fleet_calendar').id, 'calendar')],
            'domain': [('fleet_id', '=', self.fleet_id.id)],
        }
        
        
        
        






class ServiceTimesheet(models.Model):
    _name = 'service.timesheet'
    _description = 'Service Timesheet'
    _order = 'date desc'

    # Add this line to avoid conflicts with hr module
    _inherit = ['mail.thread']  # Optional: Add if you need tracking
    
    request_id = fields.Many2one('service.request', string="Service Request", required=True, ondelete='cascade')
    
    # Add employee_id to satisfy HR module requirements
    employee_id = fields.Many2one('hr.employee', string="Employee", 
                                  help="Employee who performed the work")
    
    date = fields.Date(string="Date", default=fields.Date.context_today, required=True)
    description = fields.Text(string="Work Description")
    
    role = fields.Selection([
        ('technician', 'Technician'),
        ('delivery', 'Delivery'),
        ('labor', 'Labor'),
        ('supervisor', 'Supervisor'),
        ('other', 'Other'),
    ], string="Role", required=True, default='technician')
    
    hours = fields.Float(string="Hours", required=True)
    rate = fields.Float(string="Rate", compute='_compute_rate', store=True, readonly=False)
    amount = fields.Float(string="Amount", compute='_compute_amount', store=True)
    
    company_id = fields.Many2one('res.company', string='Company', 
                                  related='request_id.company_id', store=True)

    @api.depends('role', 'request_id.partner_id')
    def _compute_rate(self):
        """Compute rate based on employee contract or default values"""
        for record in self:
            if not record.rate:
                # You can customize this logic based on your business rules
                default_rates = {
                    'technician': 50.0,
                    'delivery': 40.0,
                    'labor': 30.0,
                    'supervisor': 75.0,
                    'other': 45.0,
                }
                record.rate = default_rates.get(record.role, 0.0)

    @api.depends('hours', 'rate')
    def _compute_amount(self):
        for record in self:
            record.amount = record.hours * record.rate