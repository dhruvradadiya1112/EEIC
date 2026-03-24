from odoo import models, fields, api


class ServiceDashboard(models.Model):
    _name = 'service.dashboard'
    _description = 'Service Dashboard'

    name = fields.Char(default="Dashboard")

    # Stats
    total_requests = fields.Integer(compute="_compute_statistics")
    draft_count = fields.Integer(compute="_compute_statistics")
    assigned_count = fields.Integer(compute="_compute_statistics")
    progress_count = fields.Integer(compute="_compute_statistics")
    done_count = fields.Integer(compute="_compute_statistics")
    cancel_count = fields.Integer(compute="_compute_statistics")

    total_hours = fields.Float(compute="_compute_statistics")
    total_amount = fields.Float(compute="_compute_statistics")

    completion_rate = fields.Float(compute="_compute_statistics")

    # Recent records
    recent_requests = fields.Many2many(
        'service.request',
        compute="_compute_recent_requests"
    )

    # ======================
    # COMPUTE METHODS
    # ======================
    @api.depends_context('uid')
    def _compute_statistics(self):
        for rec in self:
            requests = self.env['service.request'].search([])

            rec.total_requests = len(requests)
            rec.draft_count = len(requests.filtered(lambda r: r.state == 'draft'))
            rec.assigned_count = len(requests.filtered(lambda r: r.state == 'assigned'))
            rec.progress_count = len(requests.filtered(lambda r: r.state == 'in_progress'))
            rec.done_count = len(requests.filtered(lambda r: r.state == 'done'))
            rec.cancel_count = len(requests.filtered(lambda r: r.state == 'cancelled'))

            rec.total_hours = sum(requests.mapped('total_hours'))
            rec.total_amount = sum(requests.mapped('total_amount'))

            rec.completion_rate = (
                (rec.done_count / rec.total_requests) * 100
                if rec.total_requests else 0
            )

    def _compute_recent_requests(self):
        for rec in self:
            rec.recent_requests = self.env['service.request'].search([], limit=5, order='id desc')

    # ======================
    # ACTIONS
    # ======================
    def action_refresh(self):
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_create_request(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'service.request',
            'view_mode': 'form',
            'target': 'current',
        }
        
        
    def action_open_assigned(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Assigned Requests',
            'res_model': 'service.request',
            'view_mode': 'list,form',
            'domain': [('state', '=', 'assigned')],
        }


    def action_open_progress(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'In Progress Requests',
            'res_model': 'service.request',
            'view_mode': 'list,form',
            'domain': [('state', '=', 'in_progress')],
        }
    
    
    def action_open_draft(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Draft Requests',
            'res_model': 'service.request',
            'view_mode': 'list,form',
            'domain': [('state', '=', 'draft')],
        }
    
    
    def action_open_done(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Done Requests',
            'res_model': 'service.request',
            'view_mode': 'list,form',
            'domain': [('state', '=', 'done')],
        }
    
    
    def action_open_cancel(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Cancelled Requests',
            'res_model': 'service.request',
            'view_mode': 'list,form',
            'domain': [('state', '=', 'cancelled')],
        }
    
    
    def action_open_requests(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'All Requests',
            'res_model': 'service.request',
            'view_mode': 'list,form',
        }
    
    