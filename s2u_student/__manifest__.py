{
    'name': 'Odoo Student',
    'version': '13.0.1.1',
    'author': 'Solutions2use',
    'price': 0.0,
    'currency': 'EUR',
    'maintainer': 'Solutions2use',
    'support': 'info@solutions2use.com',
    'images': ['static/description/app_logo.png', 'static/description/icon.png'],
    'license': 'OPL-1',
    'website': 'https://www.solutions2use.com',
    'category':  'Website',
    'summary': 'Module for teacher/students sharing video content (elearning using Vimeo)',
    'description':
        """With this module teachers can share content online with there students. You need a pro account on Vimeo (or higher). This is the only way 
        to secure your videos.              
        
        e-learning
        elearning
        vimeo
        video        
        """,
    'depends': ['base', 'website', 'project'],
    'data': [
        #'security/res_groups.xml',
        #'security/rules.xml',
        #'security/ir.model.access.csv',
        #'views/assets.xml',
        #'views/menus.xml',
        #'views/student_view.xml',
        #'views/website_templates.xml',
        #'views_inherited/project_portal_templates.xml',
        #'data/crons.xml'
    ],
    'qweb': [
    ],
    'installable': True,
    'auto_install': False,
}
