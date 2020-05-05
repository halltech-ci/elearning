# -*- coding: utf-8 -*-

import uuid
import logging

from odoo.exceptions import UserError, ValidationError
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class StudentContentType(models.Model):
    _name = 's2u.student.content.type'
    _description = 'eLearning Content Category'
    _order = 'sequence, name'

    name = fields.Char('Content Category', required=True, translate=True)
    sequence = fields.Integer()


class StudentContentVimeo(models.Model):
    _name = "s2u.student.content.vimeo"
    _inherit = 'image.mixin'
    _description = "Student Content Vimeo"
    _order = 'content_type_id, display_order, create_date desc, id desc'

    def _compute_temp_url(self):

        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')

        for record in self:
            record.temp_url = '%s/student/vimeo/content/%d/%s.mp4' % (base_url, record.id, record.access_token)

    def _get_default_access_token(self):
        return str(uuid.uuid4())

    def unlink(self):

        for record in self:
            if not record.vimeo_uri:
                continue
            self.env['s2u.vimeo.services'].vimeo_delete_video(record.vimeo_uri)

        return super(StudentContentVimeo, self).unlink()

    def write(self, vals):

        if 'active' in vals:
            for record in self:
                if not vals['active']:
                    if record.vimeo_uri:
                        self.env['s2u.vimeo.services'].vimeo_delete_video(record.vimeo_uri)
        return super(StudentContentVimeo, self).write(vals)

    def user_has_access(self):

        self.ensure_one()

        if self.user_ids:
            if self.env.user.id in self.user_ids.ids:
                return True

        if self.group_ids:
            groups = [g.id for g in self.group_ids]
            query = """
                        SELECT r.gid FROM res_groups_users_rel r  
                            WHERE r.gid IN %s AND r.uid = %s                                        
            """
            self.env.cr.execute(query, (tuple(groups), self.env.user.id))
            res = self.env.cr.fetchall()
            if res:
                return True
        return False

    def get_students(self):

        students = False
        self.env.cr.execute(
            """SELECT res_id FROM ir_model_data WHERE module='s2u_student' AND name='group_student'""")
        res = self.env.cr.fetchall()
        if res:
            group_id = res[0][0]
            query = """
                   SELECT r.uid FROM res_groups_users_rel r  
                       WHERE r.gid = %s                                        
            """
            self.env.cr.execute(query, (group_id,))
            res = self.env.cr.fetchall()
            if res:
                user_ids = [r[0] for r in res]
                students = self.env['res.users'].sudo().search([('id', 'in', user_ids)])
        return students

    def get_teacher_ids_of_user(self):

        if self.env.user.has_group('s2u_student.group_teacher'):
            return [self.env.user.id]
        else:
            self.env.cr.execute(
                """SELECT res_id FROM ir_model_data WHERE module='s2u_student' AND name='group_teacher'""")
            res = self.env.cr.fetchall()
            group_id = res[0][0]
            query = """
                               SELECT r.uid FROM res_groups_users_rel r  
                                   WHERE r.gid = %s                                        
                        """
            self.env.cr.execute(query, (group_id,))
            res = self.env.cr.fetchall()
            if res:
                user_ids = [r[0] for r in res]
                return user_ids
        return [0]

    def _get_content_levels(self):

        return [
            ('100', _('Level 100')),
            ('200', _('Level 200')),
            ('300', _('Level 300')),
            ('400', _('Level 400')),
        ]

    def _get_content_stars(self):

        return [
            ('0', _('None')),
            ('1', _('1 star')),
            ('2', _('2 stars')),
            ('3', _('3 stars')),
        ]

    # indirection to ease inheritance
    _content_level_selection = lambda self, *args, **kwargs: self._get_content_levels(*args, **kwargs)
    _content_stars_selection = lambda self, *args, **kwargs: self._get_content_stars(*args, **kwargs)

    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env.user.company_id, readolny=True)
    teacher_id = fields.Many2one('res.users', string='Teacher', required=True,
                                 default=lambda self: self.env.user, readolny=True, states={'draft': [('readonly', False)]})
    name = fields.Char(string='Title', required=True, readonly=True, states={'draft': [('readonly', False)]})
    description = fields.Text(string='Description', readonly=True, states={'draft': [('readonly', False)]})
    content_type = fields.Selection([
        ('video', 'Video'),
        ('page', 'Page'),
    ], required=True, default='video', string='Type', readonly=True, states={'draft': [('readonly', False)]})
    content_target = fields.Selection([
        ('elearning', 'e-Learning'),
        ('personal', 'Personal'),
    ], required=True, default='elearning', string='Target', readonly=True, states={'draft': [('readonly', False)]})
    group_ids = fields.Many2many('res.groups', 's2u_res_groups_student_content_vimeo_rel', 'content_id', 'group_id',
                                 string='Access for groups')
    user_ids = fields.Many2many('res.users', 's2u_res_users_student_content_vimeo_rel', 'content_id', 'user_id',
                                string='Access for users')
    student_id = fields.Many2one('res.users', string='Student', readonly=True, states={'draft': [('readonly', False)]})
    project_id = fields.Many2one('project.project', string='Project', readonly=True, states={'draft': [('readonly', False)]})
    task_id = fields.Many2one('project.task', string='Task')
    vimeo_uri = fields.Char(string='Uri', copy=False)
    vimeo_html = fields.Text(string='Embedding', copy=False)
    vimeo_data = fields.Binary(string='Video', readonly=True, states={'draft': [('readonly', False)]}, copy=False)
    vimeo_filename = fields.Char(string='File Name', copy=False)
    vimeo_checksum = fields.Char(string="Checksum/SHA1", copy=False)
    vimeo_use_external_pull_link = fields.Boolean(string='External pull')
    vimeo_external_url = fields.Char("External url", copy=False)
    page_url = fields.Char(string='Page', copy=False, readonly=True, states={'draft': [('readonly', False)]})
    active = fields.Boolean(default=True, copy=False)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('sync', 'Synchronizing'),
        ('publish', 'Published'),
        ('offline', 'Offline'),
    ], required=True, default='draft', string='State', index=True, copy=False)
    temp_url = fields.Char(string='Temp. url', readonly=True, compute='_compute_temp_url')
    access_token = fields.Char('Security Token', copy=False, default=_get_default_access_token)
    image_1920 = fields.Image(readonly=True, states={'draft': [('readonly', False)]}, copy=False)
    tot_views = fields.Integer(string="# views", default=0)
    website_published = fields.Boolean(string="Website published", default=False)
    display_order = fields.Integer(string="Display order", required=True, default=1)
    level = fields.Selection(_content_level_selection, required=True, default='100', string='Level', copy=False)
    stars = fields.Selection(_content_stars_selection, required=True, default='0', string='Stars', copy=False)
    content_type_id = fields.Many2one('s2u.student.content.type', string='Category')

    def _create_task(self):

        self.ensure_one()

        if not self.project_id:
            return False

        content = '<p>%s</p><br/><br/><br/>' % self.description
        if self.content_type == 'page':
            url = '<a href="%s">%s</a>' % (self.page_url, self.name)
            content = '%s%s' % (content, url)

        students = []
        if self.user_ids:
            for u in self.user_ids:
                students.append(u.partner_id.id)

        if self.group_ids:
            groups = [g.id for g in self.group_ids]
            query = """
                        SELECT r.uid FROM res_groups_users_rel r  
                            WHERE r.gid IN %s                                        
            """
            self.env.cr.execute(query, (tuple(groups),))
            res = self.env.cr.fetchall()
            users_in_groups = [r[0] for r in res]
            for u in self.env['res.users'].browse(users_in_groups):
                students.append(u.partner_id.id)

        students = list(set(students))
        for student in students:
            values = {
                'project_id': self.project_id.id,
                'name': self.name,
                'description': content,
                'partner_id': student,
                'user_id': self.teacher_id.id,
                's2u_content_id': self.id
            }

            task = self.env['project.task'].search([('s2u_content_id', '=', self.id),
                                                    ('partner_id', '=', student)])
            if task:
                task.write(values)
            else:
                task = self.env['project.task'].create(values)

            add_followers_ids = [student]
            task.message_subscribe(add_followers_ids)

        return True

    def publish_content(self):

        self.ensure_one()

        if self.state == 'draft':
            if not self.group_ids and not self.user_ids:
                raise UserError(_("Please select a group or user who have access to this content!"))

            if self.content_type == 'video':
                if self.vimeo_use_external_pull_link:
                    if self.vimeo_uri:
                        res = self.env['s2u.vimeo.services'].vimeo_update_video(self)
                        if res:
                            self.write({
                                'state': 'sync'
                            })
                    else:
                        res = self.env['s2u.vimeo.services'].vimeo_upload_video_pull(self)
                        if res:
                            self.write({
                                'vimeo_uri': res['uri'],
                                'vimeo_html': res['embed']['html'],
                                'state': 'sync',
                                'vimeo_checksum': False
                            })
                            self.env['s2u.vimeo.services'].vimeo_add_whitelist(self.vimeo_uri,
                                                                               self.env['s2u.vimeo.services'].get_whitelist_domain())
                            self.env['s2u.vimeo.services'].vimeo_change_folder(self.vimeo_uri)
                            self.env['s2u.vimeo.services'].vimeo_get_thumbnails(self.vimeo_uri)
                            self.write({
                                'state': 'sync'
                            })
                else:
                    if not self.vimeo_data:
                        raise UserError(_("No video present to publish!"))

                    content_data = self.env['ir.attachment'].sudo().search([('res_model', '=', 's2u.student.content.vimeo'),
                                                                            ('res_field', '=', 'vimeo_data'),
                                                                            ('res_id', '=', self.id)])
                    if not (content_data.checksum == self.vimeo_checksum):
                        res = self.env['s2u.vimeo.services'].vimeo_upload_video_pull(self)
                        if res:
                            self.write({
                                'vimeo_uri': res['uri'],
                                'vimeo_html': res['embed']['html'],
                                'state': 'sync',
                                'vimeo_checksum': content_data.checksum
                            })
                            self.env['s2u.vimeo.services'].vimeo_add_whitelist(self.vimeo_uri,
                                                                               self.env['s2u.vimeo.services'].get_whitelist_domain())
                            self.env['s2u.vimeo.services'].vimeo_change_folder(self.vimeo_uri)
                            self.env['s2u.vimeo.services'].vimeo_get_thumbnails(self.vimeo_uri)
                    else:
                        res = self.env['s2u.vimeo.services'].vimeo_update_video(self)
                        if res:
                            self.write({
                                'state': 'sync'
                            })

                return True

            if self.content_type == 'page':
                self.write({
                    'state': 'publish',
                    'website_published': True
                })

                if self.content_target == 'personal':
                    self._create_task()

            return True

    def unpublish_content(self):

        self.ensure_one()

        if self.content_target == 'personal':
            task = self.env['project.task'].sudo().search([('s2u_content_id', '=', self.id)])
            if task:
                task.write({
                    'active': False
                })

        self.write({
            'state': 'draft',
            'website_published': False
        })

    @api.model
    def cron_synchronize(self):
        """WARNING: meant for cron usage only - will commit() after each validation!"""

        _logger.info('Start synchronize with Vimeo ...')

        self._cr.commit()

        todos = self.search([('state', '=', 'sync')], limit=5)
        for t in todos:

            if t.content_type != 'video':
                continue

            try:
                res = self.env['s2u.vimeo.services'].vimeo_get_video(t.vimeo_uri)
                if res and res['upload']['status'] == 'complete':
                    if not t.image_1920:
                        image = self.env['s2u.vimeo.services'].vimeo_get_thumbnails(t.vimeo_uri)
                        if image:
                            t.write({
                                'image_1920': image
                            })
                    t.write({
                        'state': 'publish',
                        'website_published': True
                    })

                    if t.content_target == 'personal':
                        t._create_task()

                self._cr.commit()
            except Exception as e:
                self._cr.rollback()
                _logger.error('Vimeo synchronization [%s] failed for object: [%s] with id: [%d]' % (t.vimeo_uri, t.name, t.id))
