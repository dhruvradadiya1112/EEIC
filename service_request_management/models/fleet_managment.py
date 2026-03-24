from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError



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
    _order = 'scheduled_date desc'

    fleet_id = fields.Many2one('fleet.managment', string="Fleet", required=True)
    service_request_id = fields.Many2one('service.request', string="Service Request")

    name = fields.Char(string="Reference")
    user_id = fields.Many2one('res.users', string="Assigned User")

    scheduled_date = fields.Date(string="Scheduled_date")


    state = fields.Selection([
        ('draft', 'Draft'),
        ('assigned', 'Assigned'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
        ('approved', 'approved'),
        ('cancelled', 'Cancelled'),
    ], default='draft', string='Status', tracking=True)
    
    
    



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
        
