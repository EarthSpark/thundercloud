// -*- coding: utf-8 -*-
// Copyright © 2013-2016 SparkMeter, Inc.
// All Rights Reserved.
//

var base = require('base.js');

function TariffForm() {
    this._init();
}

exports.TariffForm = TariffForm;

// Namespace for the delegated handlers below, so that re-initializing the form
// -- which the tariff modal does every time it renders the fragment -- rebinds
// them instead of stacking a second copy on `document`.
var EVENTS = '.tariffform';

TariffForm.prototype = {
    _init: function() {
        $(document).off(EVENTS);

        $(document).on('change' + EVENTS, 'input:radio[id^="tariff_type"]', function(event) {
            $("div.tariff_type").addClass("hide");
            $("div.tariff_type." + $(this).val()).removeClass("hide");
            $("input#tariff_type[value='flat']").attr('checked', $(this).val() === 'flat');
            $("input#tariff_type[value='blockrate']").attr('checked', $(this).val() === 'blockrate');
        });

        $(document).on('change' + EVENTS, 'input:radio[id^="load_limit_type"]', function(event) {
            $("div.load_limit_type").addClass("hide");
            $("div.load_limit_type." + $(this).val()).removeClass("hide");
            $("input#load_limit_type[value='flat']").attr('checked', $(this).val() === 'flat');
            $("input#load_limit_type[value='scheduled']").attr('checked', $(this).val() === 'scheduled');
            if (this.checked) {
                $(".load-limits").removeClass("hide");
            } else {
                $(".load-limits").addClass("hide");
            }
        });

        $(document).on('change' + EVENTS, 'input:checkbox[id^="tou_enabled"]', function(event) {
            if (this.checked) {
                $(".tou").removeClass("hide");
            } else {
                $(".tou").addClass("hide");
            }
        });

        $(document).on('change' + EVENTS, 'input:checkbox[id^="plan_enabled"]', function(event) {
            if (this.checked) {
                $(".plan-price").removeClass("hide");
                $(".plan-fixed-fee").removeClass("hide");
            } else {
                $(".plan-price").addClass("hide");
                $(".plan-fixed-fee").addClass("hide");
            }
        });

        $(document).on('change' + EVENTS, 'input:checkbox[id^="daily_energy_limit_enabled"]', function(event) {
            if (this.checked) {
                $(".daily-energy-limit-reset-hour").removeClass("hide");
                $(".daily-energy-limit-value").removeClass("hide");
            } else {
                $(".daily-energy-limit-reset-hour").addClass("hide");
                $(".daily-energy-limit-value").addClass("hide");
            }
        });

        // scheduled load limits
        new TableModalHelper({
            modal: '#loadLimitModal',
            table: '#tariff-load-limits',
            state_field: 'form #load_limits',
            fields: ['start', 'end', 'value'],
            defaults: function(objects) {
                var max_end = 0;
                var min_start = 24;
                var start, end;
                for (var i = 0; i < objects.length; i++) {
                    end = parseInt(objects[i].end.slice(0, 2), 10);
                    if (end > max_end) {
                        max_end = end;
                    }
                    start = parseInt(objects[i].start.slice(0, 2), 10);
                    if (start < min_start) {
                        min_start = start;
                    }
                }
                start = max_end;
                end = min_start;
                return [base.pad(start, 2) + ':00', base.pad(end, 2) + ':00', '100'];
            },
            title: $('#tariff-form-params').attr('data-load-limits-title'),
            objects: JSON.parse($('#tariff-form-params').attr('data-load-limits'))
        });

        // blockrates
        new TableModalHelper({
            modal: '#blockrateModal',
            table: '#tariff-blockrates',
            state_field: 'form #blockrates',
            fields: ['lower', 'upper', 'value'],
            title: JSON.parse($('#tariff-form-params').attr('data-blockrates-title')),
            objects: JSON.parse($('#tariff-form-params').attr('data-blockrates'))
        });

        // tous
        new TableModalHelper({
            modal: '#touModal',
            table: '#tariff-tous',
            state_field: 'form #tous',
            fields: ['start', 'end', 'value'],
            defaults: function(objects) {
                var max_end = 0;
                var min_start = 24;
                var start, end;
                for (var i = 0; i < objects.length; i++) {
                    end = parseInt(objects[i].end.slice(0, 2), 10);
                    if (end > max_end) {
                        max_end = end;
                    }
                    start = parseInt(objects[i].start.slice(0, 2), 10);
                    if (start < min_start) {
                        min_start = start;
                    }
                }
                start = max_end;
                end = min_start;
                return [base.pad(start, 2) + ':00',
                    base.pad(end, 2) + ':00',
                    '100'];
            },
            title: $('#tariff-form-params').attr('data-tous-title'),
            objects: JSON.parse($('#tariff-form-params').attr('data-tous'))
        });

        // Removes the negative symbol when values are entered
        $('.no-negative').on('focusout', function() {
            fieldRegEx(this);
        });
    }
};

// FIXME: properly scope these functions
function uuid4() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(
        /[xy]/g, function(c) {
            var r = Math.random() * 16 | 0;
            var v = c === 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
        });
}

function TableModalHelper(params) {
    this._init(params);
    return this;
}

exports.TableModalHelper = TableModalHelper;

// Future field restrictions can be created in this function
function fieldRegEx(field) {
    var neg = /\-/;
    var fieldObj = $(field);
    var value = $(fieldObj[0]).val();

    // Removes the negative symbol
    if ($(fieldObj[0]).hasClass('no-negative')) {
        return $(fieldObj[0]).val(value.replace(neg, ''));
    }
}

exports.fieldRegEx = fieldRegEx;
TableModalHelper.prototype = {
    _init: function(params) {
        this.params = params;
        this.modal = $(params.modal);
        this.table = $(params.table);
        // console.log(this.params, this.modal, this.table);
        this._setup();
    },

    _setup: function() {
        var obj, td;

        if (this.params.objects) {
            for (var i = 0; i < this.params.objects.length; i += 1) {
                obj = this.params.objects[i];
                td = this._append_table_row(obj);
                this._summarize_row(td, obj);
                this._update_form_field(td, obj);
            }
        }

        this.modal.find('button#save').on('click',
            this._on_button_save__click.bind(this));
        var me = this;
        this.table.on('click', '#add-modal', function(event) {
            me._on_table__click_add_modal(event, me);
        });
        this.table.on('click', '#edit-modal', function(event) {
            me._on_table__click_edit_modal(event, me);
        });
        this.table.on('click', '#delete-row', function(event) {
            me._on_table__click_delete_row(event, me);
        });
    },

    _new_object: function() {
        var obj = {id: uuid4()};
        for (var i = 0; i < this.params.fields.length; i += 1) {
            var field = this.params.fields[i];
            var value = this._get_default_field_value(i);
            obj[field] = value;
        }
        return obj;
    },

    _open_modal: function(obj) {
        this._update_modal_fields(obj);
        this.modal.find('.modal-title').text(this.params.title);
    },

    _read_modal_fields: function() {
        var obj = {id: this.modal.find('input#id').val()};
        for (var i = 0; i < this.params.fields.length; i += 1) {
            var field = this.params.fields[i];
            var value = this.modal.find('input#' + field).val();
            if (field === "lower" || field === "upper") {
                value = parseInt(value, 10) || 0;
            } else if (field === "value") {
                value = parseFloat(value) || 0.0;
            }
            obj[field] = value;
        }
        return obj;
    },

    _get_default_field_value: function(i) {
        var value;
        if ('defaults' in this.params) {
            var objs = $(this.params.state_field).val() || "{}";
            var retval = this.params.defaults(JSON.parse(objs));
            value = retval[i];
        } else {
            value = "";
        }
        return value;
    },

    _reset_modal_fields: function() {
        for (var i = 0; i < this.params.fields.length; i += 1) {
            var field = this.params.fields[i];
            var value = this._get_default_field_value(i);
            this.modal.find('input#' + field).text(value);
        }
    },

    _update_modal_fields: function(obj) {
        for (var i = 0; i < this.params.fields.length; i += 1) {
            var field = this.params.fields[i];
            var value = obj[field];
            this.modal.find('input#' + field).val(value);
        }
        this.modal.find('input#id').val(obj.id);
    },

    _append_table_row: function(object) {
        var html = '<tr>';
        for (var i = 0; i < this.params.fields.length; i += 1) {
            var field = this.params.fields[i];
            html += '<td>' + object[field] + '</td>';
        }
        html += '<td style="width: 50px">';

        html += '<div class="btn-group">' +
            '<button class="btn btn-xs btn-default dropdown-toggle" data-toggle="dropdown"><i class="icon-cog"></i></button>' +
            '<ul class="dropdown-menu">' +
            '<li><a id="edit-modal" href="#" data-toggle="modal" data-target="#' +
            this.modal.attr('id') + '">Edit</a></li>' +
            '<li class="divider"></li>' +
            '<li><a id="delete-row" href="#">Delete</a></li>' +
            '</ul>' +
            '</div>';

        html += '</td>';
        html += '</tr>';

        this.table.find('> tbody:last').append(html);
        return this.table.find('td:last');
    },

    _update_form_field: function() {
        var data = [];
        this.table.find('tr[data-object]').each(
            function() {
                var obj = JSON.parse($(this).attr("data-object"));
                if (!$.isEmptyObject(obj)) {
                    data.push(obj);
                }
            });
        $(this.params.state_field).val(JSON.stringify(data));
    },

    _summarize_row: function(td, obj) {
        var tr = td.parent('tr');
        // console.log('summarize', td, tr, obj);
        tr.attr('data-object', JSON.stringify(obj));
        tr.attr('data-id', obj.id);
    },

    // Callbacks

    _on_table__click_add_modal: function(event, me) {
        var obj = me._new_object();
        me._open_modal(obj);
    },

    _on_table__click_edit_modal: function(event, me) {
        var tr = $(event.target).closest('tr');
        // console.assert(tr.length >= 0);
        var obj = JSON.parse(tr.attr('data-object'));
        me._open_modal(obj);
    },

    _on_table__click_delete_row: function(event) {
        event.preventDefault();
        var tr = $(event.target).closest('tr');
        tr.remove();
        this._update_form_field();
    },

    _on_button_save__click: function(event) {
        this.modal.modal('hide');

        var obj = this._read_modal_fields();
        this._reset_modal_fields();

        var selector = this.table.find('tr[data-id="' + obj.id + '"]');
        var td;
        if (selector.length) {
            var children = selector.children();
            for (var i = 0; i < this.params.fields.length; i += 1) {
                var field = this.params.fields[i];
                $(children.get(i)).text(obj[field]);
            }
            // edit column
            td = $(children.get(this.params.fields.length));
        } else {
            td = this._append_table_row(obj);
        }
        this._summarize_row(td, obj);
        this._update_form_field();
    }

};
