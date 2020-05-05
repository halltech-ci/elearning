# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools, SUPERUSER_ID, _
from odoo.exceptions import UserError, AccessError, ValidationError
from odoo.tools.safe_eval import safe_eval
from odoo.tools.misc import format_date


class Task(models.Model):
    _inherit = "project.task"

    def _compute_vimeo_embed(self):

        for record in self:
            record.s2u_vimeo_embed = False
            if record.s2u_content_id and record.s2u_content_id.state == 'publish' and record.s2u_content_id.content_type == 'video':
                record.s2u_vimeo_embed = record.s2u_content_id.vimeo_html

    s2u_vimeo_embed = fields.Char(string='Vimeo embed', readonly=True, compute='_compute_vimeo_embed')
    s2u_content_id = fields.Many2one('s2u.student.content.vimeo', string='Content vimeo', ondelete='cascade')

