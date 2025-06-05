# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import _, http
from odoo.http import request, Response
from odoo.exceptions import UserError
from datetime import datetime
from markupsafe import Markup
from odoo.addons.website_slides.controllers.main import WebsiteSlides


class WebsiteSlidesORA(WebsiteSlides):

    @http.route('/ora/response/save/', type='http', auth="user", website=True)
    def save_response(self, **kwargs):
        slide_id = int(kwargs.get('slide_id'))
        submit_action = kwargs.get('submit')
        slide = request.env['slide.slide'].sudo().browse(slide_id)
        user_response = self._get_access_data(kwargs)

        if submit_action == 'save':
            self.add_answers(kwargs, user_response)

        elif submit_action == 'resubmit_fresh':
            self._get_access_data(kwargs, resubmit=True)
            user_response.state = 'inactive'

        elif submit_action == 'resubmit_copy':
            resubmit_copy_response = self._get_access_data(kwargs, resubmit=True)
            self.add_answers(kwargs, resubmit_copy_response)
            user_response.state = 'inactive'

        elif submit_action == 'submit':
            if len(user_response) > 1:
                user_response = user_response[-1]

            user_response.write({
                'state': 'submitted',
                'submitted_date': datetime.now()
            })

            self.add_answers(kwargs, user_response)
            if slide.peer_assessment:
                peer_users = self._assign_peer_review_users(slide, user_response)
                if slide.notify_peer:
                    self._notify_peer_users(slide, user_response, peer_users)
            else:
                if slide.notify_staff:
                    self._notify_staff(slide, user_response)

        return request.redirect('/slides/slide/%s' % request.env['ir.http']._slug(slide))

    def _assign_peer_review_users(self, slide, user_response):
        enrolled_users = slide.channel_id.partner_ids.filtered(
            lambda p: p.id != request.env.user.partner_id.id
        )
        peer_limit = min(slide.peer_limit, len(enrolled_users))
        peer_users = []

        for _ in range(peer_limit):
            peer_user = slide._get_peer_user(user_response)
            if peer_user:
                peer_users.append(peer_user)
                request.env['open.response.rubric.staff'].create({
                    'assess_type': 'peer',
                    'user_id': peer_user.id,
                    'state': 'in_progress',
                    'response_id': user_response.id
                })

        return peer_users

    def _notify_peer_users(self, slide, user_response, peer_users):
        for peer in peer_users:
            base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
            action = request.env.ref('website_ora_elearning.action_ora_response')
            url = f"{base_url}/odoo/action-{action.id}/{user_response.id}"
            msg = request.env['mail.message'].create({
                'model': 'res.partner',
                'res_id': peer.partner_id.id,
                'message_type': 'comment',
                'subtype_id': request.env.ref('mail.mt_comment').id,
                'author_id': request.env.user.partner_id.id,
                'body': f"""
                    <p><strong>{user_response.user_id.partner_id.name}</strong> has submitted an assessment for the ORA content titled <strong>{slide.name}</strong>.</p>
                    <p>We kindly request you to review and rate the submission at your earliest convenience.</p>
                    <div style="padding: 16px 8px; text-align: center;">
                        <a href="{url}"
                        style="background-color: #875a7b; padding: 8px 16px; text-decoration: none; color: #fff; border-radius: 5px;">
                            View ORA Response
                        </a>
                    </div>
                    <p>Thank you for your valuable time and feedback.</p>
                    <br/>
                    <p>Best regards,<br/>
                    {user_response.user_id.partner_id.name or ''}</p>
                    """,
            })
            request.env['mail.notification'].create({
                'author_id': msg.author_id.id,
                'mail_message_id': msg.id,
                'res_partner_id': peer.partner_id.id,
                'notification_type': 'inbox',
                'notification_status': 'sent',
            })
            template = request.env.ref('website_ora_elearning.email_template_peer_review_submitted')
            if template:
                template.sudo().with_context(
                    user_response_id=user_response.id,
                    peer_user_email=peer.partner_id.email,
                    peer_user_name=peer.partner_id.name,
                    user_id=request.env.user.id,
                    user_name=request.env.user.name,
                    slide_name=slide.name,
                ).send_mail(peer.id, force_send=True)

    def _notify_staff(self, slide, user_response):
        staff = user_response.staff_id
        if not staff:
            raise UserError(_('No peer users and staff are available for assessment. Please try again later.'))

        base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
        action = request.env.ref('website_ora_elearning.action_ora_response')
        url = f"{base_url}/odoo/action-{action.id}/{user_response.id}"
        msg = request.env['mail.message'].create({
            'model': 'res.partner',
            'res_id': slide.user_id.partner_id.id,
            'message_type': 'comment',
            'subtype_id': request.env.ref('mail.mt_comment').id,
            'author_id': request.env.user.partner_id.id,
            'body': f"""
                <p><strong>{user_response.user_id.partner_id.name}</strong> has submitted an assessment for the ORA content titled <strong>{slide.name}</strong>.</p>
                <p>We kindly request you to review and rate the submission at your earliest convenience.</p>
                <div style="padding: 16px 8px; text-align: center;">
                    <a href="{url}"
                    style="background-color: #875a7b; padding: 8px 16px; text-decoration: none; color: #fff; border-radius: 5px;">
                        View ORA Response
                    </a>
                </div>
                <p>Thank you for your valuable time and feedback.</p>
                <br/>
                <p>Best regards,<br/>
                {user_response.user_id.partner_id.name or ''}</p>
                """,
        })
        request.env['mail.notification'].create({
            'author_id': msg.author_id.id,
            'mail_message_id': msg.id,
            'res_partner_id': slide.user_id.partner_id.id,
            'notification_type': 'inbox',
            'notification_status': 'sent',
        })
        template = request.env.ref('website_ora_elearning.email_template_staff_review_submitted')
        if template:
            template.sudo().with_context(
                user_response_id=user_response.id,
                staff_name = user_response.staff_id.name,
                staff_email = user_response.staff_id.partner_id.email,
                user_id=request.env.user.id,
                user_name=request.env.user.name,
                slide_name=slide.name,
            ).send_mail(staff.id, force_send=True)

    def _get_access_data(self, post, resubmit=False):
        user = request.env.user
        slide_id = request.env['slide.slide'].sudo().browse(int(post.get('slide_id')))
        if slide_id.response_ids and not resubmit:
            response = slide_id.response_ids.filtered(lambda x: x.state in ['active', 'submitted'] and x.user_id == user)
            if response:
                return response
        response = slide_id._create_answer(request.env.user.id)
        return response

    def add_answers(self, kwargs, response):
        if kwargs.get('response_id'):
            old_user_response = request.env['ora.response'].browse(int(kwargs.get('response_id')))
            for line in response.user_response_line:
                for oline in old_user_response.user_response_line:
                    if line.prompt_id == oline.prompt_id:
                        if line.response_type == 'text':
                            line.value_text_box = oline.value_text_box
                        elif line.response_type == 'rich_text':
                            line.value_richtext_box = Markup(oline.value_richtext_box)
        else:
            for line in response.user_response_line:
                if line.response_type == 'text':
                    line.value_text_box = kwargs[str(line.prompt_id.id)]
                elif line.response_type == 'rich_text':
                    line.value_richtext_box = Markup(kwargs[str(line.prompt_id.id)])
                    # query = ("update open_response_user_line set value_richtext_box='%s' where id='%s'") % (Markup(kwargs[str(line.prompt_id.id)]), line.id)
                    # request.cr.execute(query)

    def _prepare_additional_channel_values(self, values, **kwargs):
        values = super(WebsiteSlidesORA, self)._prepare_additional_channel_values(values, **kwargs)
        slide = values.get('slide')
        submitted = False
        if slide and slide.prompt_ids:
            values.update({
                'slide_prompts': [{
                    'id': prompt.id,
                    'sequence': prompt.sequence,
                    'question': Markup(prompt.question_name),
                    'response_type': prompt.response_type,
                    'submitted': submitted,
                    'name': prompt.name,
                } for prompt in slide.prompt_ids.sorted(key=lambda x: x.id)]
            })
        if slide and slide.response_ids:
            total_responses = slide.response_ids.filtered(lambda l: l.user_id == request.env.user)
            submitted_response = total_responses.filtered(lambda l: l.state == 'submitted')
            active_response = total_responses.filtered(lambda l: l.state == 'active')
            inactive_response = total_responses.filtered(lambda l: l.state == 'inactive')
            assessed_response = total_responses.filtered(lambda l: l.state == 'assessed')
            values['submitted_response'] = submitted_response
            values['active_response'] = active_response
            values['inactive_response'] = inactive_response
            values['total_responses'] = total_responses
            values['assessed_response'] = assessed_response
            values['rubric_ids'] = slide.rubric_ids
            for response in total_responses:
                if response.feedback == '<p><br></p>':
                    response.feedback = False
            values['peer_responses'] = request.env['open.response.rubric.staff'].search([
                ('user_id', '=', request.env.user.id),
                ('assess_type', '=', 'peer'),
                ('response_id.state', 'in', ['submitted', 'assessed']),
                ('response_id.slide_id', '=', slide.id)
            ]).mapped('response_id')
        return values

    @http.route('/slides/slide/get_values', website=True, type="json", auth="user")
    def slide_get_value(self, slide_id):
        csrf_token = request.csrf_token()
        slide = request.env['slide.slide'].browse(slide_id)
        if slide:
            values = {'slide': self._get_slide_values(slide), 'csrf_token': csrf_token}
            if slide.prompt_ids:
                values.update({
                    'slide_prompts': [{
                        'id': prompt.id,
                        'sequence': prompt.sequence,
                        'question': Markup(prompt.question_name),
                        'response_type': prompt.response_type,
                        'name': prompt.name,
                    } for prompt in slide.prompt_ids.sorted(key=lambda x: x.id)]
                })
            if slide.response_ids:
                total_responses = slide.response_ids.filtered(lambda l: l.user_id == request.env.user)
                values['total_responses'] = []
                for ora_response in total_responses:
                    if ora_response.feedback == '<p><br></p>' or ora_response.feedback == False:
                        ora_response.feedback = ''
                    values['total_responses'].append(self._get_total_responses(ora_response, slide))
                peer_response_ids = request.env['open.response.rubric.staff'].search([
                    ('user_id', '=', request.env.user.id),
                    ('assess_type', '=', 'peer'),
                    ('response_id.state', 'in', ['submitted', 'assessed']),
                    ('response_id.slide_id', '=', slide.id)
                ])
                values['peer_responses'] = []
                for staff_response in peer_response_ids:
                    submitted_date = False
                    if staff_response.submitted_date:
                        submitted_date = staff_response.submitted_date.strftime('%d %B %Y')
                    values['peer_responses'].append(({
                        'id': staff_response.response_id.id,
                        'state': staff_response.state,
                        'assess_type': staff_response.assess_type,
                        'user_id': staff_response.user_id.id,
                        'submitted_date': submitted_date,
                        'option_ids': [{
                            'id': rubric_id.criteria_id.id,
                            'criterian_name': rubric_id.criteria_id.criterian_name,
                            'criteria_desc': rubric_id.criteria_desc,
                            'name': rubric_id.option_id.name,
                            'criteria_option_point': rubric_id.criteria_option_point,
                            'criteria_option_desc': rubric_id.criteria_option_desc,
                            'assess_explanation': rubric_id.assess_explanation,
                        } for rubric_id in staff_response.option_ids],
                        'user_response_line': [self._get_user_response(user_response_line) for user_response_line in staff_response.response_id.user_response_line]
                    }))
        return values

    def _get_slide_values(self, slide):
        next_slide = slide.channel_id.slide_content_ids[((slide.channel_id.slide_content_ids.ids).index(slide.id))+1] if ((slide.channel_id.slide_content_ids.ids).index(slide.id)) < len(slide.channel_id.slide_content_ids.ids) - 1 else None
        return {
            'id': slide.id,
            'is_member': slide.channel_id.is_member,
            'is_preview': slide.is_preview,
            'peer_assessment': slide.peer_assessment,
            'completed': (request.env['slide.slide.partner'].sudo().search([('slide_id', '=', slide.id),('partner_id', '=', request.env.user.partner_id.id)])).completed,
            'hasNext' : next_slide if next_slide else None,
            'ispro' : 1 if 'is_sequential' in request.env['slide.channel']._fields else None,
            'next_slide_url': '/slides/slide/%s?fullscreen=1' % request.env['ir.http']._slug(next_slide) if next_slide else None,
            'user': request.env.user.id,
            'rubric_ids': [{
                'criterian_name': rubric.criterian_name,
                'name': rubric.name,
                'id': rubric.id,
                'criterian_ids': [{
                    'id': option.id,
                    'name': option.name,
                } for option in rubric.criterian_ids],
            }for rubric in slide.rubric_ids],
        }

    def _get_user_response(self, user_response_line):
        return {
            'id': user_response_line.id,
            'prompt_id': user_response_line.prompt_id.id,
            'value_text_box': user_response_line.value_text_box,
            'value_richtext_box': Markup(user_response_line.value_richtext_box),
        }

    def _get_total_responses(self, ora_response, slide):
        submitted_date = False
        if ora_response.submitted_date:
            submitted_date = ora_response.submitted_date.strftime('%d %B %Y')
        return {
            'id': ora_response.id,
            'user': request.env.user.id,
            'state': ora_response.state,
            'feedback': Markup(ora_response.feedback),
            'staff_id': ora_response.sudo().staff_id.id,
            'staff_name': ora_response.sudo().staff_id.name,
            'user_name': ora_response.sudo().user_id.name,
            'submitted_date': submitted_date,
            'can_resubmit': ora_response.can_resubmit,
            'feedback_user_image_url': request.website.image_url(ora_response.sudo().staff_id, 'image_1920', size=256),
            'ora_res_user_image_url': request.website.image_url(ora_response.sudo().user_id, 'image_1920', size=256),
            'user_response_line': [self._get_user_response(user_response_line) for user_response_line in ora_response.user_response_line],
            'slide_rubric_staff_line': [{
                'state': staff_line.state,
                'assess_type': staff_line.assess_type,
                'user_id': staff_line.sudo().user_id.id,
                'option_ids': [{
                    'id': rubric_id.criteria_id.id,
                    'criterian_name': rubric_id.criteria_id.criterian_name,
                    'criteria_desc': rubric_id.criteria_desc,
                    'name': rubric_id.option_id.name,
                    'criteria_option_point': rubric_id.criteria_option_point,
                    'criteria_option_desc': rubric_id.criteria_option_desc,
                    'assess_explanation': rubric_id.assess_explanation,
                } for rubric_id in staff_line.option_ids],
            }for staff_line in ora_response.slide_rubric_staff_line],
            'rubric_ids': [{
                'criterian_name': rubric.criterian_name,
                'name': rubric.name,
                'id': rubric.id,
                'criterian_ids': [{
                    'id': option.id,
                    'name': option.name,
                } for option in rubric.criterian_ids],
            }for rubric in slide.rubric_ids],
    }

    @http.route('/submit/peer/response', type='http', auth="user", website=True)
    def submit_peer_response(self, **kwargs):
        slide = request.env['slide.slide'].sudo().browse(int(kwargs.get('slide_id')))
        response_id = int(kwargs.get('response_id'))
        response = request.env['ora.response'].browse(response_id)

        self._submit_peer_review(response, request.env.user, kwargs)

        if self._all_peers_completed(response) and slide.notify_staff:
            self._notify_staff_on_peer_completion(response, slide)

        return request.redirect('/slides/slide/%s' % request.env['ir.http']._slug(slide))

    def _submit_peer_review(self, response, user, kwargs):
        for line in response.slide_rubric_staff_line:
            if line.user_id == user and line.assess_type == 'peer':
                values = []
                for criteria in response.slide_id.rubric_ids:
                    opt_key = f'options_{response.id}_{criteria.id}'
                    exp_key = f'exp_{response.id}_{criteria.id}'
                    option_id = kwargs.get(opt_key)
                    values.append((0, 0, {
                        'criteria_id': criteria.id,
                        'option_id': int(option_id) if option_id else False,
                        'assess_explanation': kwargs.get(exp_key)
                    }))
                line.option_ids = values
                line.state = 'completed'
                line.submitted_date = datetime.now()

    def _all_peers_completed(self, response):
        peer_lines = response.slide_rubric_staff_line.filtered(lambda l: l.assess_type == 'peer')
        return all(l.state == 'completed' for l in peer_lines)

    def _notify_staff_on_peer_completion(self, response, slide):
        peer_lines = response.slide_rubric_staff_line.filtered(lambda l: l.assess_type == 'peer' and l.state == 'completed')
        peer_names = [l.user_id.name for l in peer_lines]
        peer_emails = [l.user_id.email for l in peer_lines]

        peer_email_str = ", ".join(peer_emails) if peer_emails else "No peers found"

        template = request.env.ref('website_ora_elearning.mail_template_peer_assessment_completed')
        if template:
            template.sudo().with_context(
                user_response_id=response.id,
                user_email=response.user_id.email,
                slide_name=slide.name,
                peer_emails=peer_email_str
            ).send_mail(response.id, force_send=True)

        peer_name_str = self._format_peer_names(peer_names)
        base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
        action = request.env.ref('website_ora_elearning.action_ora_response')
        url = f"{base_url}/odoo/action-{action.id}/{response.id}"

        msg = request.env['mail.message'].create({
            'model': 'res.partner',
            'res_id': response.user_id.sudo().partner_id.id,
            'message_type': 'comment',
            'subtype_id': request.env.ref('mail.mt_comment').id,
            'author_id': request.env.user.partner_id.id,
            'body': f"""
                <p>Dear {response.user_id.name},</p>
                <p><strong>{peer_name_str}</strong> {('has' if len(peer_names) == 1 else 'have')} submitted their peer assessment for the ORA content titled <strong>{slide.name}</strong>.</p>
                <p>We kindly request you to review and evaluate the submission at your earliest convenience.</p>
                <div style="padding: 16px 8px; text-align: center;">
                    <a href="{url}" style="background-color: #875a7b; padding: 8px 16px; text-decoration: none; color: #fff; border-radius: 5px;">
                        View ORA Response
                    </a>
                </div>
                <p>Your feedback is highly valued and contributes significantly to the learner's development.</p>
                <br/>
                <p>Best regards,<br/>{peer_name_str}</p>
            """,
        })

        request.env['mail.notification'].create({
            'author_id': msg.author_id.id,
            'mail_message_id': msg.id,
            'res_partner_id': response.user_id.sudo().partner_id.id,
            'notification_type': 'inbox',
            'notification_status': 'sent',
        })

    def _format_peer_names(self, names):
        if not names:
            return "No peers found"
        if len(names) == 1:
            return names[0]
        elif len(names) == 2:
            return f"{names[0]} and {names[1]}"
        else:
            return f"{', '.join(names[:-1])}, and {names[-1]}"

    def _get_channel_progress(self, channel, include_quiz=False):
        result = super(WebsiteSlidesORA, self)._get_channel_progress(channel, include_quiz=include_quiz)
        slides = request.env['slide.slide'].sudo().search([('channel_id', '=', channel.id)])
        ora_response_ids = request.env['ora.response'].sudo().search([
            ('slide_id', 'in', slides.ids),
            ('state', '=', 'assessed'),
            ('user_id', '=', request.env.user.id)
        ])
        for ora_response in ora_response_ids:
            result[ora_response.slide_id.id]['quiz_karma_gain'] += ora_response.xp_points
            result[ora_response.slide_id.id]['quiz_karma_won'] += ora_response.xp_points
        return result
    
    @http.route(['/slides/channel/leave'], type='json', auth='user', website=True)
    def slide_channel_leave(self, channel_id):
        slide_ids = request.env['slide.slide'].sudo().search([('channel_id','=',int(channel_id))])
        for slide_id in slide_ids:
            request.env['ora.response'].sudo().search([('user_id','=',int(request.env.uid)),('slide_id','=', int(slide_id))]).unlink()
        res = super(WebsiteSlidesORA, self).slide_channel_leave(channel_id)
        return res
