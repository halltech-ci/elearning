# -*- coding: utf-8 -*-

import requests
import json
import base64
import logging
import urllib.request

from odoo.exceptions import UserError, ValidationError
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class VimeoServices(models.TransientModel):

    _name = 's2u.vimeo.services'

    @api.model
    def dict_to_params(self, d):
        if not d:
            return ''

        params = False

        for k, v in d.items():
            if params:
                params += '&%s=%s' % (k, v)
            else:
                params = '%s=%s' % (k, v)

        if params:
            return '?' + params
        else:
            return ''

    @api.model
    def get_base_url(self, section=None):
        base_url = 'https://api.vimeo.com'
        if section:
            if section.startswith('/'):
                return '%s%s' % (base_url, section)
            else:
                return '%s/%s' % (base_url, section)
        else:
            return base_url

    @api.model
    def get_client_key(self):

        exists = self.env['ir.config_parameter'].sudo().search([('key', '=', 's2u_student.vimeo.client_key')], limit=1)
        if not exists:
            raise UserError(_('No client key defined in config parameters (s2u_student.vimeo.client_key)!'))
        return exists.value

    @api.model
    def get_client_secret(self):

        exists = self.env['ir.config_parameter'].sudo().search([('key', '=', 's2u_student.vimeo.client_secret')], limit=1)
        if not exists:
            raise UserError(_('No client secret defined in config parameters (s2u_student.vimeo.client_secret)!'))
        return exists.value

    @api.model
    def get_client_token(self):

        exists = self.env['ir.config_parameter'].sudo().search([('key', '=', 's2u_student.vimeo.client_token')], limit=1)
        if not exists:
            raise UserError(_('No client token defined in config parameters (s2u_student.vimeo.client_token)!'))
        return exists.value

    @api.model
    def get_client_folder(self):

        exists = self.env['ir.config_parameter'].sudo().search([('key', '=', 's2u_student.vimeo.client_folder')], limit=1)
        if exists:
            return exists.value
        else:
            return False

    @api.model
    def get_whitelist_domain(self):

        exists = self.env['ir.config_parameter'].sudo().search([('key', '=', 's2u_student.vimeo.whitelist_domain')],
                                                               limit=1)
        if exists:
            return exists.value
        else:
            return 'localhost'

    @api.model
    def vimeo_upload_video_pull(self, content):

        url = self.get_base_url(section='/me/videos')

        if content.vimeo_use_external_pull_link:
            data = {
                "description": content.description if content.description else '',
                "name": content.name,
                "embed": {
                    "buttons": {
                        "embed": False,
                        "fullscreen": True,
                        "like": False,
                        "share": False,
                        "watchlater": False,
                    },
                    "logos": {
                        "vimeo": False,
                    },
                    "title": {
                        "name": "hide",
                        "owner": "hide",
                        "portrait": "hide"
                    },
                },
                "privacy": {
                    "add": False,
                    "comments": "nobody",
                    "download": False,
                    "embed": "whitelist",
                    "view": "unlisted",
                },
                "upload": {
                    "approach": "pull",
                    "size": 1,
                    "link": content.vimeo_external_url
                }
            }
        else:
            content_data = self.env['ir.attachment'].sudo().search([('res_model', '=', 's2u.student.content.vimeo'),
                                                                    ('res_field', '=', 'vimeo_data'),
                                                                    ('res_id', '=', content.id)])
            if not content_data:
                return False

            data = {
                "description": content.description if content.description else '',
                "name": content.name,
                "embed": {
                    "buttons": {
                        "embed": False,
                        "fullscreen": True,
                        "like": False,
                        "share": False,
                        "watchlater": False,
                    },
                    "logos": {
                        "vimeo": False,
                    },
                    "title": {
                        "name": "hide",
                        "owner": "hide",
                        "portrait": "hide"
                    },
                },
                "privacy": {
                    "add": False,
                    "comments": "nobody",
                    "download": False,
                    "embed": "whitelist",
                    "view": "unlisted",
                },
                "upload": {
                    "approach": "pull",
                    "size": str(content_data.file_size),
                    "link": content.temp_url
                }
            }

        response = requests.post(url,
                                 data=json.dumps(data),
                                 headers={
                                     "Authorization": "Bearer %s" % self.get_client_token(),
                                     "Content-Type": "application/json",
                                     "Accept": "application/vnd.vimeo.*+json;version=3.4"
                                 })
        if response.status_code == 201:
            return json.loads(response.content.decode('utf-8'))
        else:
            _logger.debug(response.content)
            return False

    @api.model
    def vimeo_update_video(self, content):

        if content.content_type != 'video':
            return True

        if not content.vimeo_uri:
            return True

        url = '%s%s' % (self.get_base_url(), content.vimeo_uri)

        data = {
            "description": content.description if content.description else '',
            "name": content.name,
        }

        response = requests.patch(url,
                                 data=json.dumps(data),
                                 headers={
                                     "Authorization": "Bearer %s" % self.get_client_token(),
                                     "Content-Type": "application/json",
                                     "Accept": "application/vnd.vimeo.*+json;version=3.4"
                                 })
        if response.status_code == 200:
            return True
        else:
            _logger.debug(response.content)
            return False

    @api.model
    def vimeo_change_folder(self, uri):

        if not uri:
            return False

        if not self.get_client_folder():
            return True

        url = '%s/%s%s' % (self.get_base_url(section='/me/projects'), self.get_client_folder(), uri)
        response = requests.put(url,
                                headers={
                                    "Content-Type": "application/json",
                                    "Authorization": "Bearer %s" % self.get_client_token()
                                })
        if response.status_code == 204:
            return True
        else:
            _logger.debug(response.content)
            return False

    @api.model
    def vimeo_add_whitelist(self, uri, domain):

        if not uri:
            return False
        if not domain:
            return False
        url = '%s%s/privacy/domains/%s' % (self.get_base_url(), uri, domain)
        response = requests.put(url,
                                headers={
                                    "Content-Type": "application/json",
                                    "Authorization": "Bearer %s" % self.get_client_token()
                                })
        if response.status_code == 204:
            return True
        else:
            _logger.debug(response.content)
            return False

    @api.model
    def vimeo_get_video(self, uri):

        if not uri:
            return False
        url = '%s%s' % (self.get_base_url(), uri)
        response = requests.get(url,
                                headers={
                                    "Content-Type": "application/json",
                                    "Authorization": "Bearer %s" % self.get_client_token()
                                })
        if response.status_code == 200:
            res = json.loads(response.content.decode('utf-8'))
            return res
        else:
            _logger.debug(response.content)
            return False

    @api.model
    def vimeo_delete_video(self, uri):

        if not uri:
            return False
        url = '%s%s' % (self.get_base_url(), uri)
        response = requests.delete(url,
                                headers={
                                    "Content-Type": "application/json",
                                    "Authorization": "Bearer %s" % self.get_client_token()
                                })
        if response.status_code == 204:
            return True
        else:
            _logger.debug(response.content)
            return False

    @api.model
    def vimeo_get_thumbnails(self, uri):

        if not uri:
            return False
        url = '%s%s/pictures' % (self.get_base_url(), uri)
        response = requests.get(url,
                                headers={
                                    "Content-Type": "application/json",
                                    "Authorization": "Bearer %s" % self.get_client_token()
                                })
        if response.status_code == 200:
            res = json.loads(response.content.decode('utf-8'))
            if res['total'] > 0:
                link = False
                for picture in res['data']:
                    if not picture['active']:
                        continue
                    width = False
                    for size in picture['sizes']:
                        if not width or size['width'] > width:
                            width = size['width']
                            link = size['link']
                    break
                if link:
                    try:
                        request = urllib.request.Request(link)
                        request.add_header("Authorization", "Bearer %s" % self.get_client_token())
                        response = urllib.request.urlopen(request)
                        image = response.read()
                        if image:
                            return base64.b64encode(image)
                        else:
                            return False
                    except:
                        return False
                else:
                    return False
            else:
                return False
        else:
            _logger.debug(response.content)
            return False





