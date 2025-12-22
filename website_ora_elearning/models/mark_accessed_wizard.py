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
    response_assess_id = fields.Many2one(
        'open.response.rubric.staff',
        ondelete="cascade",
        string="Response Assessment"
    )
    assess_line_ids = fields.One2many('rubric.assess.line.wizard', 'wizard_id', string="Rubric Lines")

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
        # Step 0: Update explanation values from request.params (manual textarea capture)
        post_data = self.env.context.get('params') or {}
        for line in self.assess_line_ids:
            textarea_key = f'assess_explanation_{line.id}'
            if textarea_key in post_data:
                line.assess_explanation = post_data[textarea_key]

        # Step 1: Validations
        if not self.response_id:
            raise UserError("Response not found.")

        slide = self.response_id.slide_id
        if not slide:
            raise UserError("Slide not linked to response.")

        if self.response_id.state != 'submitted':
            raise UserError("Only submitted slides can be assessed.")

        for line in self.assess_line_ids:
            if not (line.criteria_id and line.option_id):
                raise UserError("Please fill in all required rubric fields before confirming assessment.")

        # Step 2: Create the staff assessment parent record
        staff_assess = self.env['open.response.rubric.staff'].create({
            'response_id': self.response_id.id,
            'assess_type': 'staff',
            'user_id': self.env.user.id,
            'state': 'completed',
        })

        total_score = 0

        # Step 3: Create rubric assess lines
        for line in self.assess_line_ids:
            point = line.option_id.option_points or 0
            total_score += point

            self.env['open.response.rubric.assess'].create({
                'response_assess_id': staff_assess.id,
                'criteria_id': line.criteria_id.id,
                'option_id': line.option_id.id,
                'assess_explanation': line.assess_explanation or '',
                'criteria_option_point': point,
            })

        # Step 4: Update total score
        staff_assess.total_score = total_score

        # Step 5: Update response state and give karma
        self.response_id.state = 'assessed'
        slide.sudo().user_id.karma += self.response_id.xp_points or 0

        # Step 6: Send email and notification
        if slide.notify_user:
            # template = self.env.ref('website_ora_elearning.email_template_assessment_completed')
            # base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            # action = self.env.ref('website_ora_elearning.action_ora_response')
            # url = f"{base_url}/odoo/action-{action.id}/{self.response_id.id}"
            email_values = {
                'email_cc': False,
                'auto_delete': False,
                'message_type': 'user_notification',
                'scheduled_date': False,
                'partner_ids': [],
                'email_to': self.response_id.user_id.partner_id.email_formatted,
            }
            email_template = self.env.ref('website_ora_elearning.email_template_assessment_completed', raise_if_not_found=False).sudo()
            email_template.sudo().with_context(
                slide_name=slide.name,
                user_email=self.response_id.user_id.email_formatted,
                user_name=self.response_id.user_id.name,
                staff_name=self.response_id.staff_id.sudo().partner_id.name,
                url=slide.website_url + '?fullscreen=1#',
                company_email = self.env.company.email_formatted,
            ).send_mail(self.response_id.id, force_send=True, email_values=email_values)

            # msg = self.env['mail.message'].create({
            #     'model': 'res.partner',
            #     'res_id': slide.user_id.partner_id.id,
            #     'message_type': 'comment',
            #     'subtype_id': self.env.ref('mail.mt_comment').id,
            #     'author_id': self.env.user.partner_id.id,
            #     'body': f"""
            #         <p>Your assessment for the ORA content <strong>{slide.name}</strong> has been reviewed and evaluated by staff member <strong>{self.response_id.staff_id.sudo().partner_id.name}</strong>.</p>
            #         <div style="padding: 16px 8px; text-align: center;">
            #             <a href="{url}" style="background-color: #875a7b; padding: 8px 16px; text-decoration: none; color: #fff; border-radius: 5px;">
            #                 View ORA Response
            #             </a>
            #         </div>
            #         <p>We hope you enjoy this feedback and continue learning with us!</p>
            #         <br/>
            #         <p>Best regards,<br/>
            #         {self.response_id.user_id.partner_id.name or ''}</p>
            #     """,
            # })
            # self.env['mail.notification'].create({
            #     'author_id': msg.author_id.id,
            #     'mail_message_id': msg.id,
            #     'res_partner_id': slide.user_id.partner_id.id,
            #     'notification_type': 'inbox',
            #     'notification_status': 'sent',
            # })

        return {'type': 'ir.actions.act_window_close'}


    
class RubricAssessLineWizard(models.TransientModel):
    _name = 'rubric.assess.line.wizard'
    _description = 'Rubric Assess Line Wizard'

    wizard_id = fields.Many2one('mark.assessed.wizard', string="Wizard")
    criteria_id = fields.Many2one('open.response.rubric', string="Criteria", readonly=True)
    option_id = fields.Many2one('rubric.criterian', "Option", domain="[('rubric_id', '=', criteria_id)]")
    criteria_option_point = fields.Integer(related='option_id.option_points')
    assess_explanation = fields.Text(string="Assess Explanation")