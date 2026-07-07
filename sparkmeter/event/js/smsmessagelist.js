// -*- coding: utf-8 -*-
// Copyright © 2013-2016 SparkMeter, Inc.
// All Rights Reserved.
//
// Message history list
var datatables = require('datatables.js');
var base = require('base.js');
var backend = require('backend.js').backend;

function escape_html(html) {
    return html.replace(/&/g, '&amp;')
        .replace(/>/g, '&gt;')
        .replace(/</g, '&lt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&apos;');
}

function render_tooltip(tooltip, text) {
    var html = '<span data-toggle="tooltip" title="';
    html += escape_html(tooltip);
    html += '">';
    html += escape_html(text);
    html += '</span>';
    return html;
}

function MessageList() {
    this._init();
}

exports.MessageList = MessageList;

MessageList.prototype = {
    columns: [
        {title: 'Date', data: 'timestamp', type: 'string'},
        {
            title: 'Type', type: 'string',
            render: function(data, type, row) {
                // Two-way SMS received and the code (e.g. BAL) has been recognized
                // Response to a valid Two-way SMS code (e.g. BAL) from a valid number
                if (row.code) {
                    return row.code;
                    // Any system message (verify number, error message, etc)
                } else if (row.message_type) {
                    return "System";
                    // Message sent as the result of an alert (e.g. Low balance)
                } else if (row.alert_label) {
                    return row.alert_label;
                    // Two-way SMS received but not recognized (unrecognized phone number)
                } else {
                    return "N/A";
                }
            }
        },
        {
            title: 'In/Out', data: 'direction', type: 'string',
            render: function(data, type, row) {
                if (type === 'display') {
                    if (row.direction === 'in') {
                        return 'In';
                    } else if (row.direction === 'out') {
                        return 'Out';
                    }
                } else {
                    return row.direction;
                }
            }
        },
        {
            title: 'To/From', name: 'to-from', type: 'string',
            render: function(data, type, row) {
                if (type === 'display') {
                    if (row.customer_name !== null) {
                        return render_tooltip("Phone number: " + row.phone_number,
                            row.customer_name);
                    } else {
                        return row.phone_number;
                    }
                } else {
                    return row.customer_name;
                }
            }
        },
        {title: 'Customer name', data: 'customer_name', type: 'string', visible: false},
        {title: 'Phone number', data: 'phone_number', type: 'string', visible: false},
        {title: 'Message', data: 'text', type: 'string'},
        {
            title: 'Processed', data: 'processed', type: 'string',
            render: function(data, type, row) {
                if (row.processed) {
                    return 'Yes';
                } else {
                    return 'No';
                }
            }
        },
        {title: 'Event type', data: 'event_type', type: 'string', visible: false},
        {title: 'Message Type', data: 'message_type', type: 'string', visible: false},
        {title: 'Origin', data: 'origin', type: 'string', visible: false},
        {title: 'Ground', data: 'ground_name', type: 'string', className: 'ground'}
    ],

    _init: function() {
        var groundName = base.getMetaItemProps('ground');

        this._table = this._createDataTable();
        // Check if are on a meter page, look for the meter dashboard widget,
        // which is a bit of a hack.
        if ($('.icon-dashboard').length > 0) {
            var column = this._table.column('to-from:name');
            column.visible(false);
        }
        this._groundDropDown = new datatables.GroundDropDown();
        this._groundDropDown.populateGrounds(groundName);
        this._setTableTitle(groundName);
    },

    _setTableTitle: function(groundName) {
        if (groundName !== 'null') {
            var tableElement = this._table.table().node();
            var titleElement = $(tableElement).parents('.box').find('.box-header span.title');
            titleElement.text('Message History on ' + groundName);
        }
    },

    _createDataTable: function() {
        var table = datatables.create_table($('table#message-list'), {
            bPaginate: true,
            columns: this.columns,
            bServerSide: true,
            ajax: function(data, callback, settings) {
                backend.getMessages(data).then(function(results) {
                    callback(results);
                });
            },
            iDisplayLength: 100,
            oSearch: {
                bSmart: false,
                bRegex: true
            },
            rowCallback: function(node, row, index) {
                var status;
                if (row.processed) {
                    status = 'status-success';
                } else {
                    status = 'status-pending';
                }
                $(node).addClass(status);
            },
            order: [[0, "desc"]],
            initComplete: function() {
                this._groundDropDown.createTableFilter(table);
                // Since we're doing SSR, we should manually debounce the search input
                var searchTerm = '';
                $('#message-list_filter input').unbind().bind('change', function(_) {
                    searchTerm = $(this).val();
                    table.search(searchTerm).draw();
                }).on('input', base.debounce(function() {
                    if ($(this).val() !== searchTerm) {
                        $(this).trigger('change');
                    }
                }, 400));
                $('#message-list-export-all').bind('click', function(e) {
                    e.target.href = e.target.dataset.href + '?' + $.param(table.ajax.params());
                });
            }.bind(this)
        }, {
            export_csv: true,
            fixed_header: false,
            export_columns: [0, 1, 2, 4, 5, 6, 7, 8, 9, 10, 11] // if this changes, change the export endpoint
        });
        return table;
    }
};
