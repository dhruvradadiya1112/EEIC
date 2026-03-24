from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError


class ResUsers(models.Model):
    _inherit = 'res.users'

    is_service_user = fields.Boolean(string="Service Management")
    
    
    
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
    
    
    
    
    is_fleet_required = fields.Boolean(string="Fleet Required",tracking=True)
    fleet_id = fields.Many2one('fleet.managment', string="Fleet", tracking=True)
    fleet_scheduled_date = fields.Datetime(string="From Date & Time",tracking=True)
    
    
    
    scheduled_date = fields.Date(string="Scheduled Date",required=True)
    
    
    
    @api.constrains('is_fleet_required', 'fleet_id', 'fleet_scheduled_date')
    def _check_fleet_fields(self):
        for rec in self:
            if rec.is_fleet_required:
                if not rec.fleet_id:
                    raise ValidationError("Please select a Fleet.")
                if not rec.fleet_scheduled_date:
                    raise ValidationError("Please set Date & Time.")
            
            
    

   
            
            
            
            
    # @api.constrains('fleet_id', 'fleet_scheduled_date')
    # def _check_fleet_availability(self):
    #     for rec in self:
    #         if rec.fleet_id and rec.fleet_scheduled_date:
    #             domain = [
    #                 ('fleet_id', '=', rec.fleet_id.id),
    #                 ('id', '!=', rec.id),
    #                 ('scheduled_date', '<', rec.fleet_scheduled_date),
    #             ]
    #             if self.search_count(domain):
    #                 raise ValidationError("This fleet is already assigned in this Date.")
            
            
                              








    def _compute_invoice_count(self):
        for rec in self:
            rec.invoice_count = 1 if rec.invoice_id else 0
        
        
    def write(self, vals):
        res = super().write(vals)
    
        if 'state' in vals:
            for rec in self:
                history = self.env['fleet.history'].search([
                    ('service_request_id', '=', rec.id)
                ])
    
                history.write({
                    'state': rec.state
                })
    
        return res


    
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
        
        self.state = 'assigned'
    
        for rec in self:
            if rec.fleet_id and rec.fleet_scheduled_date:
                self.env['fleet.history'].create({
                    'fleet_id': rec.fleet_id.id,
                    'service_request_id': rec.id,
                    'name': rec.name,
                    'user_id': rec.user_id.id,
                    'scheduled_date': rec.fleet_scheduled_date,
                    'state':rec.state
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
    
    
    assign_history_ids = fields.One2many('service.assign.history','request_id',string="Assign History")
    
    
        
    def action_open_assign_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Assign User',
            'res_model': 'service.assign.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_request_id': self.id,
                'default_new_user_id': self.user_id.id,
            }
        }
        
    def action_open_reschedule_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Reschedule Service',
            'res_model': 'service.reschedule.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_request_id': self.id,
                'default_scheduled_date': self.scheduled_date,
            }
        }
    
    
    
    
    
    
class ServiceAssignHistory(models.Model):
    _name = 'service.assign.history'
    _description = 'Service Assign History'
    _order = 'create_date desc'

    request_id = fields.Many2one('service.request', string="Service Request")
    
    old_user_id = fields.Many2one('res.users', string="Previous User")
    new_user_id = fields.Many2one('res.users', string="New User",required=True)
    
    changed_by = fields.Many2one('res.users', string="Changed By", default=lambda self: self.env.user)
    
    reason = fields.Text(string="Reason",required=True)
    
    
class ServiceRescheduleWizard(models.TransientModel):
    _name = 'service.reschedule.wizard'
    _description = 'Reschedule Service'

    request_id = fields.Many2one('service.request', required=True)

    scheduled_date = fields.Datetime(string="New Scheduled Date", required=True)

    def action_reschedule(self):
        self.ensure_one()

        self.request_id.write({
            'scheduled_date': self.scheduled_date,
        })

        # Optional chatter message
        self.request_id.message_post(
            body=f"""
            Rescheduled:
            New Scheduled Date: {self.scheduled_date}
            """
        )
        
        
        
        
    
class ServiceAssignWizard(models.TransientModel):
    _name = 'service.assign.wizard'
    _description = 'Assign Service Request Wizard'

    request_id = fields.Many2one('service.request', required=True)
    
    new_user_id = fields.Many2one('res.users', string="Assign To", required=True)
    reason = fields.Text(string="Reason")

    def action_assign(self):
        self.ensure_one()

        request = self.request_id

        old_user = request.user_id

        # Update user
        request.user_id = self.new_user_id.id
        request.state = 'assigned'

        # Create history
        self.env['service.assign.history'].create({
            'request_id': request.id,
            'old_user_id': old_user.id,
            'new_user_id': self.new_user_id.id,
            'changed_by': self.env.user.id,
            'reason': self.reason,
        })

        # Chatter message
        request.message_post(
            body=f"""
            Reassigned:
            From: {old_user.name if old_user else 'None'},
            To: {self.new_user_id.name},
            Changed By: {self.env.user.name},
            Reason: {self.reason or 'N/A'}
            """
        )
        
        




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