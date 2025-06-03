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
    # option_ids = fields.One2many('open.response.rubric.assess', 'response_assess_id')
    slide_rubric_staff_line = fields.One2many(
        'mark.assessed.wizard.line',
        'wizard_response_id',
        string="Rubric Lines"
    )


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
        if not self.response_id:
            raise UserError("Response not found.")

        slide = self.response_id.slide_id
        if not slide:
            raise UserError("Slide not linked to response.")

        ora_response = self.env['ora.response'].search([('slide_id','=',slide.id)])
        if ora_response.state != 'submitted':
            raise UserError("Only submitted slides can be assessed.")

        if not self.slide_rubric_staff_line:
            raise UserError("Please fill in at least one rubric line before confirming assessment.")

        # Step 1: Create a staff assessment entry (parent record)
        staff_assess = self.env['open.response.rubric.staff'].create({
            'response_id': self.response_id.id,
            'assess_type': 'staff',
            'user_id': self.env.user.id,
            'state': 'completed',
        })

        # Step 2: Create each rubric line linked to this staff assessment
        for wizard_line in self.slide_rubric_staff_line:
            self.env['open.response.rubric.assess'].create({
                'response_assess_id': staff_assess.id,
                'criteria_id': wizard_line.criteria_id.id,
                'option_id': wizard_line.option_id.id,
                'assess_explanation': wizard_line.assess_explanation,
            })

        # Step 3: Update state and karma
        ora_response.state = 'assessed'
        slide.sudo().user_id.karma += ora_response.xp_points or 0
        if not staff_assess:
            raise UserError('Staff could not be able to assess the assessment')
        else:
            template = self.env.ref('website_ora_elearning.email_template_assessment_completed')
            if template:
                template.sudo().with_context(
                    slide_name=slide.name,
                    user_email = self.env.user.email,
                    user_name = self.env.user.name,
                ).send_mail(ora_response.id, force_send=True)

            # Step 5: Post internal notification to user
            ora_response.message_post(
                body="✅ Your assessment has been assessed.",
                partner_ids=[slide.user_id.partner_id.id],
                message_type='notification',
                subtype_xmlid='mail.mt_note',
            )


class MarkAssessedWizardLine(models.TransientModel):
    _name = 'mark.assessed.wizard.line'
    _description = 'Mark Assessed Wizard Line'

    wizard_response_id = fields.Many2one('mark.assessed.wizard', ondelete="cascade")
    criteria_id = fields.Many2one('open.response.rubric', 'Criteria', required=True)
    criteria_desc = fields.Text(related='criteria_id.name')
    option_id = fields.Many2one('rubric.criterian', 'Options', required=True)
    criteria_option_desc = fields.Text(related='option_id.option_desc')
    criteria_option_point = fields.Integer(related='option_id.option_points')
    assess_explanation = fields.Text("Assess Explanation", required=True, translate=True)
    response_assess_id = fields.Many2one('open.response.rubric.staff', ondelete="cascade")