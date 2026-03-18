from odoo import models, fields, api
from odoo.exceptions import UserError


class ServiceRequest(models.Model):
    _name = 'service.request'
    _description = 'Service Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    name = fields.Char(string='Reference', default='New', readonly=True, tracking=True)
    partner_id = fields.Many2one('res.partner', string="Customer", required=True, tracking=True)
    sale_order_id = fields.Many2one('sale.order', string="Sales Order", tracking=True)
    user_id = fields.Many2one('res.users', string="Assigned To", default=lambda self: self.env.user, tracking=True)
    
    description = fields.Text(string="Description/Instructions")
    scheduled_date = fields.Date(string="Scheduled Date", required=True)
    deadline_date = fields.Date(string="Deadline", required=True)
    
    state = fields.Selection([
        ('assigned', 'Assigned'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
        ('approved', 'approved'),
        ('cancelled', 'Cancelled'),
    ], default='assigned', string='Status', tracking=True)

    timesheet_ids = fields.One2many('service.timesheet', 'request_id', string="Timesheets")
    
    total_hours = fields.Float(string="Total Hours", compute='_compute_totals', store=True)
    total_amount = fields.Float(string="Total Amount", compute='_compute_totals', store=True)
    
    company_id = fields.Many2one('res.company', string='Company', 
                                  default=lambda self: self.env.company)
    
    
    invoice_id = fields.Many2one('account.move', string="Bill", readonly=True)
    invoice_count = fields.Integer(compute="_compute_invoice_count")


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