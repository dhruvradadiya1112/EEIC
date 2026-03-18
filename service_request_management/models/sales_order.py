from odoo import models, fields, api




class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    service_request_ids = fields.Many2many('service.request', string="Assigned Service Requests")
    timesheet_ids = fields.One2many('service.timesheet', 'employee_id', string="Service Timesheets")
    
    def action_view_service_requests(self):
        """View service requests assigned to this employee"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'My Service Requests',
            'res_model': 'service.request',
            'view_mode': 'list,form',
            'domain': [('user_id', 'in', self.ids)],
            'context': {'default_user_id': [(6, 0, self.ids)]},
        }
        
        
        
        
class SaleOrder(models.Model):
    _inherit = 'sale.order'

    service_request_ids = fields.One2many('service.request', 'sale_order_id', string="Service Requests")
    service_request_count = fields.Integer(string="Service Request Count", compute='_compute_service_request_count')

    def _compute_service_request_count(self):
        for rec in self:
            rec.service_request_count = len(rec.service_request_ids)

    def action_create_service_request(self):
        """Create a new service request from sales order"""
        self.ensure_one()
        
        service_request = self.env['service.request'].create({
            'partner_id': self.partner_id.id,
            'sale_order_id': self.id,
            'description': f"Service request for {self.name}",
            'state': 'draft',
        })

        return {
            'type': 'ir.actions.act_window',
            'name': 'Service Request',
            'res_model': 'service.request',
            'res_id': service_request.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_service_requests(self):
        """View all service requests for this sales order"""
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Service Requests',
            'res_model': 'service.request',
            'view_mode': 'list,form',
            'domain': [('sale_order_id', '=', self.id)],
            'context': {'default_sale_order_id': self.id, 'default_partner_id': self.partner_id.id},
        }