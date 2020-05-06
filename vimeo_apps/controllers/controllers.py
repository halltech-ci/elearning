# -*- coding: utf-8 -*-
# from odoo import http


# class VimeoApps(http.Controller):
#     @http.route('/vimeo_apps/vimeo_apps/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/vimeo_apps/vimeo_apps/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('vimeo_apps.listing', {
#             'root': '/vimeo_apps/vimeo_apps',
#             'objects': http.request.env['vimeo_apps.vimeo_apps'].search([]),
#         })

#     @http.route('/vimeo_apps/vimeo_apps/objects/<model("vimeo_apps.vimeo_apps"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('vimeo_apps.object', {
#             'object': obj
#         })
