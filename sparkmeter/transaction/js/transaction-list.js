// -*- coding: utf-8 -*-
// Copyright © 2013-2017 SparkMeter, Inc.
// All Rights Reserved.
//

var datatables = require('datatables.js');
var backend = require('backend.js').backend;
var base = require('base.js');
var MeterUtils = require('meter/js/meter-utils.js');
var SalesAccountUtils = require('salesaccount/js/sales-account-utils');

function can_reverse_transation(state, origin, has_reversal) {
    // We can only cancel processed transactions
    if (state !== 'processed') {
        return false;
    }

    // We cannot cancel reversal transactions
    if (origin === 'reversal') {
        return false;
    }

    // Do not allow to be reversed twice
    if (has_reversal === true) {
        return false;
    }

    // Is it a vendor who is performing this action?
    if ($('meta[itemprop=config-vendor]').attr('content') === 'true') {
        return false;
    }

    return true;
}

function formatWalletDataForDisplay(item) {
    if ('meter_serial' in item) {
        return MeterUtils.formatMeterLink(item.meter_serial);
    } else if ('sales_account_name' in item) {
        return SalesAccountUtils.formatSalesAccountLink(
            item.sales_account_id, item.sales_account_name);
    }
}

function renderTransactionData(propName) {
    return function(data, type, row) {
        var item = row[propName];
        if (type === 'display' || type === 'sort') {
            return formatWalletDataForDisplay(item);
        } else if (type === 'filter') {
            return JSON.stringify(item);
        } else if (type === 'type') {
            return item.customer_name || item.sales_account_name;
        }
    };
}

function TransactionList() {
    this._init();
}

exports.TransactionList = TransactionList;

TransactionList.prototype = {
    columns: [
        {
            title: 'ID', data: 'id', type: 'string',
            render: function(data, type, row) {
                if (type === 'display') {
                    if (!can_reverse_transation(row.state, row.origin, row.has_reversal)) {
                        return data;
                    }
                    var html = data;
                    html += '<a href="#" class="pull-right" ';
                    html += '   data-toggle="modal"';
                    html += '   data-target="#reverse-modal"';
                    html += '   data-transaction-id="' + data + '">';
                    html += '  <i class="icon-remove-circle"></i>';
                    html += '</a>';
                    return html;
                } else {
                    return data;
                }
            }
        },
        {title: 'Amount', data: 'amount', type: 'num-fmt'},
        {title: 'Type', data: 'acct_type', type: 'string'},
        {title: 'From', type: 'string', render: renderTransactionData('from_data')},
        {title: 'To', type: 'string', render: renderTransactionData('to_data')},
        {
            title: 'User',
            name: 'User',
            data: 'username',
            type: 'string',
            render: function(data, type, row) {
                var username = row.username;
                if (type === 'display') {
                    return '<a href="/user/' + username + '/">' +
                        username + '</a>';
                } else {
                    return username;
                }
            }
        },
        {title: 'Reference', data: 'reference_id', type: 'string'},
        {title: 'Created', data: 'created', type: 'date'},
        {title: 'Ground', data: 'ground_name', type: 'string', className: 'ground'},
        {
            title: 'Details', type: 'string',
            orderable: false,
            render: function(data, type, row) {
                if (type === 'display') {
                    return ('<button class="btn btn-info" data-action="view" data-toggle="collapse"' +
                        'data-target="' + row.id + '">View</button>');
                } else if (type === 'filter') {
                    /* Provide filter keywords so the user can search for 'processed' etc */
                    var keywords = [];
                    if (row.state === 'processed') {
                        keywords.push('processed');
                    }
                    if (row.external_id) {
                        keywords.push('external');
                    }
                    if (row.memo) {
                        keywords.push('memo');
                    }
                    if (row.error) {
                        keywords.push('error');
                    }
                    return keywords.join(' ');
                } else {
                    return '';
                }
            }
        },
        {title: 'Source', data: 'source_name', type: 'string', visible: false},
        {title: 'State', data: 'state', type: 'string', visible: false},
        {title: 'Origin', data: 'origin', type: 'string', visible: false},
        {title: 'External', data: 'external_id', type: 'string', visible: false},
        {title: 'Memo', data: 'memo', type: 'string', visible: false},
        {title: 'Error', data: 'error', type: 'string', visible: false},
        {
            title: 'Meter Serial', type: 'string', visible: false,
            render: function(data, type, row) {
                return row.from_data.meter_serial || row.to_data.meter_serial || "";
            }
        },
        {
            title: 'Sales Account', type: 'string', visible: false,
            render: function(data, type, row) {
                return row.from_data.sales_account_name || row.to_data.sales_account_name || "";
            }
        }
    ],

    _init: function() {
        var groundName = base.getMetaItemProps('ground');

        this._table = this._createDataTable();
        this._groundDropDown = new datatables.GroundDropDown();
        this._groundDropDown.populateGrounds(groundName);
        this._listenEvents();
        this._setTableTitle(groundName);
    },

    _createDataTable: function() {
        var tableElement = $('table#transaction-list');
        var table = datatables.create_table(tableElement, {
            bPaginate: true,
            columns: this.columns,
            iDisplayLength: 100,
            oSearch: {
                bSmart: false,
                bRegex: true
            },
            bServerSide: true,
            ajax: function(data, callback, settings) {
                backend.getTransactions(data).then(function(results) {
                    callback(results);
                });
            },
            rowCallback: function(node, row, index) {
                var status;
                if (row.state === 'error') {
                    status = 'status-error';
                } else if (row.state === 'processed') {
                    status = 'status-success';
                } else if (row.state === 'pending') {
                    status = 'status-pending';
                } else if (row.state === 'reversed') {
                    status = 'status-success';
                }
                $(node).addClass(status);
                $(node).attr("data-id", row.id);
            },
            order: [[
                7, // created
                "desc"]],
            initComplete: function() {
                var salesAccountType = $('[data-sa-type]').attr('data-sa-type');

                if (salesAccountType === undefined || salesAccountType === 'global') {
                    this._groundDropDown.createTableFilter(table);
                } else {
                    $('.select-filter').closest('li').remove();
                }
                // Since we're doing SSR, we should manually debounce the search input
                var searchTerm = '';
                $('#transaction-list_filter input').unbind().bind('change', function(_) {
                    searchTerm = $(this).val();
                    table.search(searchTerm).draw();
                }).on('input', base.debounce(function() {
                    if ($(this).val() !== searchTerm) {
                        $(this).trigger('change');
                    }
                }, 400));
                $('#transaction-list-export-all').bind('click', function(e) {
                    e.target.href = e.target.dataset.href + '?' + $.param(table.ajax.params());
                });
            }.bind(this)

        }, {
            export_csv: true, fixed_header: false,
            export_columns: [
                0,  // id
                1,  // amount
                2,  // acct_type
                3,  // from
                4,  // to
                5,  // username
                6,  // reference_id
                7,  // created
                8,  // ground_name
                    // SKIP details
                10, // INVISIBLE source_name
                11, // INVISIBLE state
                12, // INVISIBLE origin
                13, // INVISIBLE external_id
                14, // INVISIBLE memo
                15, // INVISIBLE error
                16, // INVISIBLE meter_serial
                17  // INVISIBLE sales_account_name
            ]
        });
        return table;
    },

    _listenEvents: function() {
        var me = this;
        $('table#transaction-list tbody')
            .on('click', '.btn-info', function() {
                var tr = $(this).closest('tr');
                me._onButtonInfoClick(tr);
            });
        $('#reverse-modal').on('show.bs.modal', this._onReverseModalShow.bind(this));
    },

    _setTableTitle: function(groundName) {
        if (groundName !== 'null') {
            var tableElement = this._table.table().node();
            var titleElement = $(tableElement).parents('.box').find('.box-header span.title');
            titleElement.text('Transaction History on ' + groundName);
        }
    },

    _renderDetails: function(row) {
        function _item(text, data_type, label) {
            if (label === undefined) {
                label = 'info';
            }
            var e = '<span class="label label-' + label + '"';
            if (data_type !== undefined) {
                e += ' data-type="' + data_type + '"';
            }
            e += '>' + text + '</span>&nbsp;';
            return e;
        }

        var html = '';
        html += _item('Source: ' + row.source_name, 'source');
        if (row.origin === 'user') {
            html += _item('Origin: User', 'origin');
        } else if (row.origin === 'system') {
            html += _item('Origin: System', 'origin');
        } else if (row.origin === 'reversal') {
            html += _item('Origin: Reversal', 'origin');
        }
        if (row.state === 'processed') {
            html += _item('Processed', 'state', 'success');
        } else if (row.state === 'pending') {
            html += _item('Pending', 'state', 'default');
        } else if (row.state === 'error') {
            html += _item('Error: ' + row.error, 'state', 'danger');
        } else if (row.state === 'reversed') {
            html += _item('Reversed', 'state', 'success');
        }
        if (row.external_id) {
            html += _item('External ID: ' + row.external_id, 'external-id');
        }
        var customer_name = row.from_data.customer_name || row.to_data.customer_name;
        if (customer_name) {
            html += _item('Customer name: ' + customer_name);
        }
        var customer_code = row.from_data.customer_code || row.to_data.customer_code;
        if (customer_code) {
            html += _item('Customer code: ' + customer_code);
        }
        if (row.memo) {
            html += _item('Memo: ' + row.memo, 'memo');
        }
        return html;
    },

    _onButtonInfoClick: function(tr) {
        var row = this._table.row(tr);
        if (row.child.isShown()) {
            row.child.hide();
            return tr.removeClass('shown');
        } else {
            row.child(this._renderDetails(row.data()), 'transaction-details').show();
            return tr.addClass('shown');
        }
    },

    _onReverseModalShow: function(event) {
        var button = $(event.relatedTarget);
        var modal = $('#reverse-modal');

        var transaction_id = button.data('transaction-id');
        var url = "/transaction/" + transaction_id + "/reverse";
        modal.find('#reverse-link').attr("href", url);

        var row = this._table.row(button.parents("tr")).data();
        var help = 'A new transaction of {amount} from {from} to {to} will be created.';
        help = help.replace('{amount}', -row.amount);
        help = help.replace('{from}', formatWalletDataForDisplay(row.from_data));
        help = help.replace('{to}', formatWalletDataForDisplay(row.to_data));
        modal.find('#reverse-help').html(help);
    }

};
