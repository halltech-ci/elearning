# -*- coding: utf-8 -*-

import base64
import logging

from odoo import http, _
from odoo.http import request
from odoo.http import Response
from odoo.exceptions import UserError

from odoo.addons.website.controllers.main import QueryURL

_logger = logging.getLogger(__name__)

class StudentController(http.Controller):

    @http.route(['/student/vimeo/content/<int:id>/<string:token>.<string:extension>'], type='http', auth="public", methods=['GET'], website=True)
    def student_vimeo_content(self, id, token, extension, **post):

        content = request.env['s2u.student.content.vimeo'].sudo().search([('id', '=', id)])
        if content and content.content_type == 'video':
            if content.access_token == token and content.state == 'sync':
                status, headers, content = request.env['ir.http'].binary_content(
                    xmlid=None, model='s2u.student.content.vimeo', id=content[0].id, field='vimeo_data', unique=None,
                    filename=content[0].vimeo_filename, filename_field='vimeo_filename', download=None, mimetype=None, access_token=None)
                if status != 200:
                    return request.env['ir.http']._response_by_status(status, headers, content)
                else:
                    content_base64 = base64.b64decode(content)
                    headers.append(('Content-Length', len(content_base64)))
                    return request.make_response(content_base64, headers)
            else:
                return Response("Error, content not found", content_type='text/html;charset=utf-8', status=404)
        else:
            return Response("Error, content not found", content_type='text/html;charset=utf-8', status=404)

    @http.route(['/student/elearning', '/student/elearning/page/<int:page>'], type='http', auth="user", methods=['GET'], website=True)
    def student_elearning(self, page=1, **searches):

        searches.setdefault('search', '')
        searches.setdefault('type', 'all')
        searches.setdefault('sorting', 'category')

        # search domains
        domain_search = {}
        content_order = 'content_type_id, display_order, create_date desc, id desc'
        sortings = [
            {
                'id': 'category',
                'name': _('Category')
            },
            {
                'id': 'new',
                'name': _('Newest')
            },
            {
                'id': 'views',
                'name': _('Most views')
            },
        ]
        current_sorting = sortings[0]

        if searches['search']:
            domain_search['search'] = ['|', ('name', 'ilike', searches['search']), ('description', 'ilike', searches['search'])]

        if searches['sorting'] == 'new':
            content_order = 'create_date desc, name'
            current_sorting = sortings[1]
        if searches['sorting'] == 'views':
            content_order = 'tot_views desc, name'
            current_sorting = sortings[2]

        current_type = None

        def dom_without(without, teacher_ids):
            domain = [('state', "in", ['publish']), ('content_target', '=', 'elearning'), ('teacher_id', 'in', teacher_ids)]
            for key, search in domain_search.items():
                if key == 'sorting':
                    continue
                if key != without:
                    domain += search
            return domain

        if searches["type"] != 'all':
            current_type = request.env['s2u.student.content.type'].sudo().browse(int(searches['type']))
            domain_search["type"] = [("content_type_id", "=", int(searches["type"]))]

        teacher_ids = request.env['s2u.student.content.vimeo'].sudo().get_teacher_ids_of_user()
        is_teacher = request.env.user.has_group('s2u_student.group_teacher')

        domain = dom_without('type', teacher_ids)
        types = request.env['s2u.student.content.vimeo'].sudo().read_group(domain, ["id", "content_type_id"], groupby=["content_type_id"], orderby="content_type_id")
        types.insert(0, {
            'content_type_id_count': sum([int(type['content_type_id_count']) for type in types]),
            'content_type_id': ("all", _("All Categories"))
        })

        step = 12  # Number of events per page
        content_count = request.env['s2u.student.content.vimeo'].sudo().search_count(dom_without("none", teacher_ids))
        pager = request.website.pager(
            url="/student/elearning",
            url_args=searches,
            total=content_count,
            page=page,
            step=step,
            scope=5)

        if is_teacher:
            videos = request.env['s2u.student.content.vimeo'].sudo().search(dom_without("none", teacher_ids), order=content_order)
        else:
            videos = request.env['s2u.student.content.vimeo'].sudo().search(dom_without("none", teacher_ids), limit=step, offset=pager['offset'], order=content_order)

        keep = QueryURL('/student/elearning', **{key: value for key, value in searches.items() if (key == 'search' or value != 'all')})

        vals = {
            'content': videos,
            'is_teacher': is_teacher,
            'current_type': current_type,
            'types': types,
            'pager': pager,
            'searches': searches,
            'keep': keep,
            'current_sorting': current_sorting,
            'sortings': sortings,
            'content_types': request.env['s2u.student.content.type'].sudo().search([]) if is_teacher else []
        }

        return request.render('s2u_student.elearning', vals)

    @http.route(['/student/elearning/add'], type='http', auth="user", methods=['GET'], website=True)
    def student_elearning_add(self, **post):

        if not request.env.user.has_group('s2u_student.group_teacher'):
            return request.render('s2u_student.no_access', status=403)

        students = request.env['s2u.student.content.vimeo'].get_students()

        vals = {
            'vimeo_token': request.env['s2u.vimeo.services'].get_client_token(),
            'students': students
        }

        if vals['vimeo_token']:
            return request.render('s2u_student.elearning_add_content', vals)
        else:
            return request.render('s2u_student.no_access', status=403)

    @http.route('/student/elearning/add/uploaded', type='json', auth='user', website=True)
    def student_elearning_add_uploaded(self, vimeo_uri, video_title, video_descript, video_target, student_id, **kwargs):

        if not request.env.user.has_group('s2u_student.group_teacher'):
            return {
                'error': True,
                'error_mes': _('You have no rights for this action.'),
            }

        vimeo_uri = vimeo_uri.replace('https://vimeo.com', '/videos')
        vals = {
            'teacher_id': request.env.user.id,
            'name': video_title,
            'description': video_descript,
            'content_type': 'video',
            'content_target': 'personal' if video_target == 'student' else 'elearning',
            'vimeo_uri': vimeo_uri,
            'state': 'draft'
        }

        if video_target == 'student':
            project = request.env['project.project'].search([('privacy_visibility', '=', 'portal'),
                                                             ('user_id', '=', request.env.user.id)], limit=1)
            if not project:
                return {
                    'error': True,
                    'error_mes': _('No portal project available for teacher.'),
                }
            vals['project_id'] = project.id
            try:
                student_id = int(student_id)
            except:
                student_id = False
            if not project:
                return {
                    'error': True,
                    'error_mes': _('No valid student selected.'),
                }
            vals['user_ids'] = [(6, 0, [student_id])]
        else:
            request.env.cr.execute("""SELECT res_id FROM ir_model_data WHERE module='s2u_student' AND name='group_student'""")
            res = request.env.cr.fetchall()
            if res:
                groups = [res[0][0]]
            else:
                groups = False

            if groups:
                vals['group_ids'] = [(6, 0, groups)]

        content = request.env['s2u.student.content.vimeo'].create(vals)
        request.env['s2u.vimeo.services'].vimeo_add_whitelist(content.vimeo_uri,
                                                              request.env['s2u.vimeo.services'].get_whitelist_domain())
        request.env['s2u.vimeo.services'].vimeo_change_folder(content.vimeo_uri)
        request.env['s2u.vimeo.services'].vimeo_get_thumbnails(content.vimeo_uri)

        res = request.env['s2u.vimeo.services'].vimeo_get_video(content.vimeo_uri)

        content.write({
            'state': 'sync',
            'vimeo_html': res['embed']['html']
        })

        return {
            'error': False,
            'error_mes': False,
        }

    @http.route('/student/elearning/edit', type='json', auth='user', website=True)
    def student_elearning_edit(self, record_item, record_id, title, type, level, stars, descript, **kwargs):

        if not request.env.user.has_group('s2u_student.group_teacher'):
            raise UserError(_("You have no rights for this action."))

        try:
            content = request.env['s2u.student.content.vimeo'].search([('id', '=', int(record_id))], limit=1)
        except:
            content = False

        if not content:
            raise UserError(_("Content not found."))

        if content.teacher_id != request.env.user:
            raise UserError(_("Content not found."))

        try:
            content_type = request.env['s2u.student.content.type'].search([('id', '=', int(type))], limit=1)
        except:
            content_type = False

        res = request.env['s2u.vimeo.services'].vimeo_update_video(content)
        if res:
            content.write({
                'name': title,
                'content_type_id': content_type.id if content_type else False,
                'level': level,
                'stars': stars,
                'description': descript
            })

            if content.content_target == 'personal' and content.task_id:
                task = request.env['project.task'].sudo().search([('s2u_content_id', '=', self.id)])
                if task:
                    task.write({
                        'name': title,
                        'description': descript
                    })

            return {
                'error': False,
                'record_item': record_item,
                'title': title,
                'descript': descript
            }
        else:
            raise UserError(_('Update vimeo failed.'))

    @http.route('/student/elearning/delete', type='json', auth='user', website=True)
    def student_elearning_delete(self, record_item, record_id, **kwargs):

        if not request.env.user.has_group('s2u_student.group_teacher'):
            raise UserError(_('You have no rights for this action.'))

        try:
            content = request.env['s2u.student.content.vimeo'].search([('id', '=', int(record_id))], limit=1)
        except:
            content = False

        if not content:
            raise UserError(_('Content not found.'))

        if content.teacher_id != request.env.user:
            raise UserError(_('Content not found.'))

        content.unpublish_content()

        return {
            'error': False,
            'record_item': record_item,
        }

    @http.route('/student/elearning/change_order', type='json', auth='user', website=True)
    def student_elearning_change_order(self, new_order, **kwargs):

        if not request.env.user.has_group('s2u_student.group_teacher'):
            raise UserError(_('You have no rights for this action.'))

        sequence = 1
        for id in new_order:
            try:
                id = int(id)
            except:
                id = False

            if not id:
                continue
            content = request.env['s2u.student.content.vimeo'].search([('id', '=', id)], limit=1)
            if not content:
                continue

            if content.teacher_id != request.env.user:
                continue

            content.write({
                'display_order': sequence
            })
            sequence += 1

        return {
            'error': False,
        }

    @http.route(['/student/elearning/<string:content>/<int:id>'], type='http', auth="user", methods=['GET'], website=True)
    def student_elearning_content(self, content, id, **post):
        if content == 'vimeo':
            video = request.env['s2u.student.content.vimeo'].sudo().search([('state', '=', 'publish'),
                                                                            ('id', '=', id)])
            if not video:
                return request.render('s2u_student.not_found', status=404)
            if not video.user_has_access():
                return request.render('s2u_student.no_access', status=403)

            video.write({
                'tot_views': video.tot_views + 1
            })
            return request.render('s2u_student.elearning_content', {
                'content': video
            })

        if content == 'other':
            page = request.env['s2u.student.content.vimeo'].sudo().search([('state', '=', 'publish'),
                                                                           ('id', '=', id)])
            if not page:
                return request.render('s2u_student.not_found', status=404)
            if not page.user_has_access():
                return request.render('s2u_student.no_access', status=403)

            page.write({
                'tot_views': page.tot_views + 1
            })
            return request.redirect(page.page_url)

        return request.render('s2u_student.not_found', status=404)


