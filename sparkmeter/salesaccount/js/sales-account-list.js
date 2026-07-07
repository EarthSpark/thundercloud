// -*- coding: utf-8 -*-
// Copyright © 2013-2017 SparkMeter, Inc.
// All Rights Reserved.
//

var backend = require('backend.js').backend;
var base = require('base.js');
var datatables = require('datatables.js');
var SalesAccountUtils = require('salesaccount/js/sales-account-utils.js');

var ACCOUNT_TYPE_GLOBAL = 'global';
var ACCOUNT_TYPE_RESTRICTED = 'restricted';

exports.PAGE_MY = 'my';
exports.PAGE_SALES_ACCOUNT = 'all';
exports.PAGE_USER_VIEW = 'user';

function SalesAccountList(params) {
    this._init(params);
}

exports.SalesAccountList = SalesAccountList;

SalesAccountList.prototype = {
    columns: [
        {
            title: 'Name',
            name: 'name',
            render: function(data, type, row) {
                if (type === 'display') {
                    return SalesAccountUtils.formatSalesAccountLink(row.id, row.name);
                } else {
                    return row.name;
                }
            }
        },
        {
            title: 'Transaction history',
            name: 'transaction_history',
            render: function(data, type, row) {
                return (
                    row.transaction_count + ' transactions ' +
                    '(' + base.format_currency(row.transaction_total) + ') ' +
                    'in the last 30 days'
                );
            },
            exported: false
        },
        {
            title: 'Ground',
            name: 'ground',
            data: 'ground_name',
            type: 'string'
        },
        {
            title: 'Markup',
            name: 'markup',
            data: 'markup',
            type: 'num-fmt'
        },
        {
            title: 'Credit',
            name: 'credit',
            data: 'credit',
            type: 'num-fmt'
        },
        {
            title: 'Debt',
            name: 'debt',
            data: 'debt',
            type: 'num-fmt'
        },
        {
            title: 'Transaction count last 30 days',
            name: 'transaction_count',
            data: 'transaction_count',
            type: 'string',
            visible: false
        },
        {
            title: 'Transaction amount last 30 days',
            name: 'transaction_total',
            data: 'transaction_total',
            type: 'string',
            visible: false
        }
    ],

    _init: function(params) {
        this._params = params || {};
        this._createDataTables();
    },

    _createDataTables: function() {
        $('table.sales-account-list').each(function(index, elem) {
            this._createDataTable($(elem));
        }.bind(this));
    },

    _createDataTable: function(elem) {
        var accountType = elem.attr("data-account-type");
        var columns = this._getTableColumns(accountType);
        var exportColumns = this._getExportColumns(columns);
        datatables.create_table(elem, {
            columns: columns,
            ordering: false,
            ajax: function(data, callback, settings) {
                backend.getSalesAccounts(this._params.page, accountType).then(function(salesAccounts) {
                    callback({ data: salesAccounts });
                });
            }.bind(this)
        }, {
            export_csv: true,
            small_table: true,
            fixed_header: false,
            export_columns: exportColumns
        });
    },

    _getTableColumns: function(accountType) {
        return this.columns.filter(function(column) {
            switch (column.name) {
                case 'name':
                    return true;
                case 'ground':
                case 'markup':
                case 'credit':
                case 'debt':
                    return accountType === ACCOUNT_TYPE_RESTRICTED;
                case 'transaction_history':
                    return accountType === ACCOUNT_TYPE_GLOBAL;
                case 'transaction_count':
                case 'transaction_total':
                    return accountType === ACCOUNT_TYPE_GLOBAL;
            }
        });
    },

    _getExportColumns: function(columns) {
        return columns.map(function(column, i) {
            if (column.exported !== false) {
                return i;
            }
            return -1;
        }).filter(function(value) {
            return value !== -1;
        });
    }
};
