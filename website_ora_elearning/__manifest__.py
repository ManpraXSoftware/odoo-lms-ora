# -*- coding: utf-8 -*-
{
    'name': 'LMS eLearning with ORA',
    'description': 'Open Response Assessment',
    'category': 'Website/eLearning',
    'summary': 'Manage and publish an eLearning platform',
    'sequence': 10,
    'version': '2.7',
    'website': 'https://www.manprax.com',
    'author': 'ManpraX Software LLP',
    'depends': ['website_slides','mass_mailing'],
    'data': [
        'data/ir_cron_data.xml',
        'data/email_templates.xml',
        'security/ir.model.access.csv',
        'views/slide_assessment_view.xml',
        'views/slide_channel_form_view.xml',
        'views/open_response_rubric_form.xml',
        'views/templates.xml',
        'views/slide_fullscreen_view.xml',
        'views/mark_accessed_wizard.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'website_ora_elearning/static/src/scss/website_slides.scss',
            'website_ora_elearning/static/src/js/ora_fullscreen.js',
            'website_ora_elearning/static/src/js/website_ora.js',
            'website_ora_elearning/static/src/xml/slide_ora.xml',
        ],
        'web.assets_backend': [
            'website_ora_elearning/static/src/js/kanban_textarea_save.js',
            'website_ora_elearning/static/src/xml/kanban_text_widget_view.xml',
        ],
    },
    'qweb': [],
    'images': ["static/description/images/banner.png"],
    'application': True,
    'license': 'AGPL-3',
}
