# models/mark_assessed_wizard.py
from odoo import models, fields, api
from odoo.exceptions import UserError

class MarkAssessedWizard(models.TransientModel):
    _name = 'mark.assessed.wizard'
    _description = 'Wizard to confirm assessment'
    _inherit = ['mail.thread', 'mail.activity.mixin']

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
            if slide.notify_user:
                template = self.env.ref('website_ora_elearning.email_template_assessment_completed')
                if template:
                    template.sudo().with_context(
                        slide_name=slide.name,
                        user_email = self.env.user.email,
                        user_name = self.env.user.name,
                        staff_name = ora_response.staff_id.sudo().partner_id.name
                    ).send_mail(ora_response.id, force_send=True)

                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                action = self.env.ref('website_ora_elearning.action_ora_response')
                url = f"{base_url}/odoo/action-{action.id}/{ora_response.id}"
                msg = self.env['mail.message'].create({
                    'model': 'res.partner',  # or 'ora.response', 'discuss.channel', etc.
                    'res_id': slide.user_id.partner_id.id,  # record to attach to
                    'message_type': 'comment',
                    'subtype_id': self.env.ref('mail.mt_comment').id,
                    'author_id': self.env.user.partner_id.id,
                    'body': f"""
                        <p>Your assessment for the ORA content <strong>{slide.name}</strong> has been reviewed and evaluated by staff member <strong>{ora_response.staff_id.sudo().partner_id.name}</strong>.</p>
                        <div style="padding: 16px 8px; text-align: center;">
                            <a href="{url}"
                            style="background-color: #875a7b; padding: 8px 16px; text-decoration: none; color: #fff; border-radius: 5px;">
                                View ORA Response
                            </a>
                        </div>
                        <p>We hope you enjoy this feedback and continue learning with us!</p>
                        <br/>
                        <p>Best regards,<br/>
                        {ora_response.user_id.partner_id.name or ''}</p>
                    """,
                })
                self.env['mail.notification'].create({
                    'author_id': msg.author_id.id,
                    'mail_message_id': msg.id,
                    'res_partner_id': slide.user_id.partner_id.id,  # the recipient
                    'notification_type': 'inbox',  # 'inbox' shows in top-right (Discuss)
                    'notification_status': 'sent',
                })


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