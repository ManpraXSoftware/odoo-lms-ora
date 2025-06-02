# models/mark_assessed_wizard.py
from odoo import models, fields, api
from odoo.exceptions import UserError

class MarkAssessedWizard(models.TransientModel):
    _name = 'mark.assessed.wizard'
    _description = 'Wizard to confirm assessment'

    response_id = fields.Many2one('ora.response', ondelete="cascade")

    user_response_lines = fields.One2many(
        comodel_name='open.response.user.line',
        compute='_compute_user_response_lines',
        store=False
    )

    peer_staff_lines = fields.One2many(
        comodel_name='open.response.rubric.staff',
        compute='_compute_peer_staff_lines',
        store=False
    )
    
    slide_rubric_ids = fields.Many2many('open.response.rubric', string="Rubric")
    option_ids = fields.One2many('open.response.rubric.assess', 'response_assess_id')
    
    @api.depends('response_id')
    def _compute_user_response_lines(self):
        for wizard in self:
            wizard.user_response_lines = self.env['open.response.user.line'].search([
                ('response_id', '=', wizard.response_id.id)
            ])

    @api.depends('response_id')
    def _compute_peer_staff_lines(self):
        for wizard in self:
            wizard.peer_staff_lines = self.env['open.response.rubric.staff'].search([
                ('response_id', '=', wizard.response_id.id),
                ('assess_type', '=', 'peer')
            ])

    def confirm_assessment(self):
        slide = self.slide_id
        if slide.state == 'submitted':
            only_peer = True
            for line in slide.slide_rubric_staff_line:
                if line.assess_type == 'staff':
                    slide.state = 'assessed'
                    line.state = 'completed'
                    user_karma = slide.user_id.karma
                    user_karma += slide.xp_points
                    slide.sudo().user_id.karma = user_karma
                    only_peer = False
            if only_peer:
                raise UserError("Please fill the rubric first.")
