from odoo import models, fields, api
from odoo.exceptions import UserError

class MarkAssessedWizard(models.TransientModel):
    _name = 'mark.assessed.wizard'
    _description = 'Wizard to confirm assessment'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    response_id = fields.Many2one('ora.response', ondelete="cascade", string="Response")
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
    slide_id = fields.Many2one(
        'slide.slide',
        related='response_id.slide_id',
        store=False,
        readonly=True,
        string="Slide"
    )
    criteria_id = fields.Many2one(
        'open.response.rubric',
        string='Criteria',
        required=True,
        domain="[('slide_id', '=', slide_id)]"
    )
    criteria_desc = fields.Text(
        related='criteria_id.name',
        readonly=True,
        string="Criteria Description"
    )
    option_id = fields.Many2one(
        'rubric.criterian',
        string='Options',
        required=True,
        domain="[('rubric_id', '=', criteria_id)]"
    )
    criteria_option_desc = fields.Text(
        related='option_id.option_desc',
        readonly=True,
        string="Option Description"
    )
    criteria_option_point = fields.Integer(
        related='option_id.option_points',
        readonly=True,
        string="Option Points"
    )
    assess_explanation = fields.Text(
        string="Assess Explanation",
        required=True,
        translate=True
    )
    response_assess_id = fields.Many2one(
        'open.response.rubric.staff',
        ondelete="cascade",
        string="Response Assessment"
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

        if self.response_id.state != 'submitted':
            raise UserError("Only submitted slides can be assessed.")

        if not (self.criteria_id and self.option_id and self.assess_explanation):
            raise UserError("Please fill in all required rubric fields before confirming assessment.")

        # Step 1: Create a staff assessment entry (parent record)
        staff_assess = self.env['open.response.rubric.staff'].create({
            'response_id': self.response_id.id,
            'assess_type': 'staff',
            'user_id': self.env.user.id,
            'state': 'completed',
        })

        # Step 2: Create the rubric line linked to this staff assessment
        self.env['open.response.rubric.assess'].create({
            'response_assess_id': staff_assess.id,
            'criteria_id': self.criteria_id.id,
            'option_id': self.option_id.id,
            'assess_explanation': self.assess_explanation,
        })

        # Step 3: Update state and karma
        self.response_id.state = 'assessed'
        slide.sudo().user_id.karma += self.response_id.xp_points or 0
        if not staff_assess:
            raise UserError('Staff could not be able to assess the assessment')
        else:
            if slide.notify_user:
                template = self.env.ref('website_ora_elearning.email_template_assessment_completed')
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                action = self.env.ref('website_ora_elearning.action_ora_response')
                url = f"{base_url}/odoo/action-{action.id}/{self.response_id.id}"
                if template:
                    template.sudo().with_context(
                        slide_name=slide.name,
                        user_email=self.response_id.user_id.email,
                        user_name=self.response_id.user_id.name,
                        staff_name=self.response_id.staff_id.sudo().partner_id.name,
                        url=url
                    ).send_mail(self.response_id.id, force_send=True)
                msg = self.env['mail.message'].create({
                    'model': 'res.partner',
                    'res_id': slide.user_id.partner_id.id,
                    'message_type': 'comment',
                    'subtype_id': self.env.ref('mail.mt_comment').id,
                    'author_id': self.env.user.partner_id.id,
                    'body': f"""
                        <p>Your assessment for the ORA content <strong>{slide.name}</strong> has been reviewed and evaluated by staff member <strong>{self.response_id.staff_id.sudo().partner_id.name}</strong>.</p>
                        <div style="padding: 16px 8px; text-align: center;">
                            <a href="{url}"
                            style="background-color: #875a7b; padding: 8px 16px; text-decoration: none; color: #fff; border-radius: 5px;">
                                View ORA Response
                            </a>
                        </div>
                        <p>We hope you enjoy this feedback and continue learning with us!</p>
                        <br/>
                        <p>Best regards,<br/>
                        {self.response_id.user_id.partner_id.name or ''}</p>
                    """,
                })
                self.env['mail.notification'].create({
                    'author_id': msg.author_id.id,
                    'mail_message_id': msg.id,
                    'res_partner_id': slide.user_id.partner_id.id,
                    'notification_type': 'inbox',
                    'notification_status': 'sent',
                })
        return {'type': 'ir.actions.act_window_close'}