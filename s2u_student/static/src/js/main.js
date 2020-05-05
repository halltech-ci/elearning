odoo.define('s2u_student.main', function (require) {
    'use strict';

    var core = require('web.core');
    var publicWidget = require('web.public.widget');
    var _t = core._t;

    publicWidget.registry.VimeoUpload = publicWidget.Widget.extend({
        selector: '#s2u_student_upload',
        init: function () {
            this._super.apply(this, arguments);
        },

        start: function () {
            var self = this;

            var dropZone = document.getElementById('drop_zone')
            var browse = document.getElementById('browse')

            $("#drop_zone").on('dragover', function(e) {
                self.handleDragOver(e)
            });

            $("#drop_zone").on('drop', function(e) {
                self.handleFileSelect(e)
            });

            $("#browse").on('change', function(e) {
                self.handleFileSelect(e)
            });

            $("#videoTarget_all").on('change', function() {
               $('.field-select-student').hide();
            });

            $("#videoTarget_student").on('change', function() {
               $('.field-select-student').show();
            });

            // init form
            $('.field-select-student').hide();
        },

        handleFileSelect: function (evt) {
            var self = this;

            evt.stopPropagation();
            evt.preventDefault();

            var files = evt.originalEvent.dataTransfer ? evt.originalEvent.dataTransfer.files : evt.target.files;
            var results = document.getElementById('results');

            /* Clear the results div */
            while (results.hasChildNodes()) results.removeChild(results.firstChild);

            /* Rest the progress bar and show it */
            self.updateProgress(0);
            document.getElementById('progress-container').style.display = 'block';

            var error_label = _t("Error");
            var error_message;
            if (!$('#videoName').val()) {
                error_message = _t("Please enter a title for this video.");
                self.showMessage('<strong>' + error_label + '</strong>: '+ error_message, 'danger');
                $('#browse').val(null);
                return
            }

            if (!$('#videoDescription').val()) {
                error_message = _t("Please enter a description for this video.");
                self.showMessage('<strong>' + error_label + '</strong>: '+ error_message, 'danger');
                $('#browse').val(null);
                return
            }

            if (!$("input[name='videoTarget']:checked").val()) {
                error_message = _t("Please select target for this video.");
                self.showMessage('<strong>' + error_label + '</strong>: '+ error_message, 'danger');
                $('#browse').val(null);
                return
            }

            if ($("input[name='videoTarget']:checked").val() == 'student') {
                if (!$("select[name='student_id']").val()) {
                    error_message = _t("Please select a student for this video.");
                    self.showMessage('<strong>' + error_label + '</strong>: '+ error_message, 'danger');
                    $('#browse').val(null);
                    return
                }
            }

            document.getElementById('progress-container').style.display = 'block';

            /* Instantiate Vimeo Uploader */
            ;(new VimeoUpload({
                name: $('#videoName').val(),
                description: $('#videoDescription').val(),
                private: true,
                file: files[0],
                token: $('#accessToken').val(),
                upgrade_to_1080: false,
                onError: function(data) {
                    self.showMessage('<strong>' + error_label + '</strong>: ' + JSON.parse(data).error, 'danger')
                },
                onProgress: function(data) {
                    self.updateProgress(data.loaded / data.total)
                },
                onComplete: function(videoId, index) {
                    var url = 'https://vimeo.com/' + videoId

                    if (index > -1) {
                        /* The metadata contains all of the uploaded video(s) details see: https://developer.vimeo.com/api/endpoints/videos#/{video_id} */
                        url = this.metadata[index].link;

                        /* add stringify the json object for displaying in a text area */
                        var pretty = JSON.stringify(this.metadata[index], null, 2);

                        console.log(pretty) /* echo server data */
                    }

                    $('#browse').val(null);

                    self._rpc({
                        route: '/student/elearning/add/uploaded',
                        params: {
                            'vimeo_uri': url,
                            'video_title': $('#videoName').val(),
                            'video_descript': $('#videoDescription').val(),
                            'video_target': $("input[name='videoTarget']:checked").val(),
                            'student_id': $("select[name='student_id']").val()
                        },
                    }).then(function(result) {
                        error_label = _t('Upload Successful');
                        error_message = _t('The system needs some time to process the video before visible to your students.');
                        self.showMessage('<strong>' + error_label + '</strong>: ' + error_message)
                    });
                }
            })).upload()
        },

        showMessage: function (html, type) {
            var self = this;
            var results = document.getElementById('results');

            /* hide progress bar */
            document.getElementById('progress-container').style.display = 'none';

            /* display alert message */
            var element = document.createElement('div');
            element.setAttribute('class', 'alert alert-' + (type || 'success'));
            element.innerHTML = html;
            results.appendChild(element)
        },

        handleDragOver: function (evt) {
            evt.stopPropagation();
            evt.preventDefault();
            evt.originalEvent.dataTransfer.dropEffect = 'copy'
        },

        updateProgress: function (progress) {
            progress = Math.floor(progress * 100);
            var element = document.getElementById('progress');
            element.setAttribute('style', 'width:' + progress + '%');
            element.innerHTML = '&nbsp;' + progress + '%'
        }
    }),

    publicWidget.registry.ELearningContent = publicWidget.Widget.extend({
        selector: '#elearning_content',
        init: function () {
            this._super.apply(this, arguments);
        },

        start: function () {
            var self = this;

            this.init_content();

            if ($('.js-grid').length) {
                s2ustudent_sortable('.js-grid', {
                    forcePlaceholderSize: false,
                    placeholderClass: 'col-lg-4 border border-maroon'
                });

                s2ustudent_sortable('.js-grid')[0].addEventListener('sortupdate', function(e) {
                    var i;
                    var new_order = [];
                    for (i = 0; i < e.detail.destination.items.length; i++) {
                        var item = e.detail.destination.items[i];
                        new_order.push($(item).data('record'))
                    }

                     self._rpc({
                        route: '/student/elearning/change_order',
                        params: {
                            'new_order': new_order
                        },
                    }).then(function(result) {
                        self.init_content();
                    });
                })
            }
        },

        init_content: function() {
            var self = this;
            var i = 1;
            while ($('#form_content_' + i).length) {
                var button_edit = $('#btn_edit_content_' + i);
                button_edit.data('item', i)
                button_edit.click(function(evt) {
                    self.switch_edit_mode($(this).data('item'))
                });

                var button_save = $('#btn_save_content_' + i);
                button_save.data('item', i)
                button_save.click(function(evt) {
                    self.save_content($(this).data('item'))
                });

                var button_cancel = $('#btn_cancel_content_' + i);
                button_cancel.data('item', i)
                button_cancel.click(function(evt) {
                    self.cancel_content($(this).data('item'))
                });

                var button_delete = $('#btn_delete_content_' + i);
                button_delete.data('item', i)
                button_delete.click(function(evt) {
                    self.delete_content($(this).data('item'))
                });

                i++;
            }
        },

        switch_edit_mode: function (item) {
            var button_edit = $('#btn_edit_content_' + item);
            var button_save = $('#btn_save_content_' + item);
            var button_cancel = $('#btn_cancel_content_' + item);
            var form_content = $('#form_content_' + item);
            var div_content = $('#div_content_' + item);

            button_edit.addClass('d-none');
            button_save.removeClass('d-none');
            button_cancel.removeClass('d-none');
            div_content.addClass('d-none');
            form_content.removeClass('d-none');
        },

        save_content: function (item) {
            var button_edit = $('#btn_edit_content_' + item);
            var button_save = $('#btn_save_content_' + item);
            var button_cancel = $('#btn_cancel_content_' + item);
            var form_content = $('#form_content_' + item);
            var div_content = $('#div_content_' + item);

            var record_id =  $('#content_record_' + item).val();
            var content_title =  $('#content_title_' + item).val();
            var content_level =  $('#content_level_' + item).val();
            var content_type =  $('#content_type_' + item).val();
            var content_stars =  $('#content_stars_' + item).val();
            var content_descript =  $('#content_descript_' + item).val();

            this._rpc({
                route: '/student/elearning/edit',
                params: {
                    'record_item': item,
                    'record_id': record_id,
                    'title': content_title,
                    'type': content_type,
                    'level': content_level,
                    'stars': content_stars,
                    'descript': content_descript
                },
            }).then(function(result) {
                if (!result.error) {
                    $('#show_content_title_' + result.record_item).text(result.title);
                    $('#show_content_descript_' + result.record_item).text(result.descript);

                    $('#btn_edit_content_' + result.record_item).removeClass('d-none');
                    $('#btn_save_content_' + result.record_item).addClass('d-none');
                    $('#btn_cancel_content_' + result.record_item).addClass('d-none');
                    $('#div_content_' + result.record_item).removeClass('d-none');
                    $('#form_content_' + result.record_item).addClass('d-none');
                }
            });
        },

        cancel_content: function (item) {
            var button_edit = $('#btn_edit_content_' + item);
            var button_save = $('#btn_save_content_' + item);
            var button_cancel = $('#btn_cancel_content_' + item);
            var form_content = $('#form_content_' + item);
            var div_content = $('#div_content_' + item);

            button_edit.removeClass('d-none');
            button_save.addClass('d-none');
            button_cancel.addClass('d-none');
            div_content.removeClass('d-none');
            form_content.addClass('d-none');
        },

        delete_content: function (item) {
            var r = confirm("Are you sure you want to delete this content?");
            if (r) {
                var record_id =  $('#content_record_' + item).val();
                this._rpc({
                    route: '/student/elearning/delete',
                    params: {
                        'record_item': item,
                        'record_id': record_id,
                    },
                }).then(function(result) {
                    if (!result.error) {
                        $('#content_block_' + result.record_item).addClass('d-none');
                    }
                });
            }
        }
    })
});
