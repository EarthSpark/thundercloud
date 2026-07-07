// -*- coding: utf-8 -*-
// Copyright © 2013-2016 SparkMeter, Inc.
// All Rights Reserved.
//

var datatables = require('datatables.js');
var backend = require('backend.js').backend;
var base = require('base.js');

var ROLE_API = 'api';

function UserList() {
    this._init();
}

exports.UserList = UserList;

UserList.prototype = {
    columns: [
        {
            title: 'User name',
            name: 'username',
            render: function(data, type, row) {
                if (type === 'display') {
                    return base.linkify(
                        "/user/" + row.username + "/",
                        row.username,
                        {'data-username': row.username}
                    );
                } else {
                    return row.username;
                }
            }
        },
        {
            title: 'Sales Accounts',
            name: 'accounts',
            render: function(data, type, row) {
                var accounts = row.accounts.filter(function(item) {
                    return item.id !== null && item.name !== null;
                });
                if (type === 'display') {
                    return accounts.map(function(account) {
                        return base.linkify(
                            "/sales-account/" + account.id + "/",
                            account.name,
                            {'data-name': account.name}
                        );
                    }).join('<br>');
                } else {
                    return accounts.map(function(account) {
                        return account.name;
                    }).join(', ');
                }
            }
        },
        {
            title: 'Email',
            name: 'email',
            data: 'email',
            type: 'string'
        },
        {
            title: 'Permissions',
            name: 'permissions',
            render: function(data, type, row) {
                var accounts = row.accounts.filter(function(item) {
                    return item.id !== null && item.name !== null;
                });
                if (accounts.length > 0) {
                    return 'Can sell electricity';
                } else {
                    return '';
                }
            }
        },
        {
            title: 'Active',
            name: 'active',
            render: datatables.boolRenderer('active')
        },
        {
            title: 'Markup',
            name: 'markup',
            data: 'markup',
            type: 'num-fmt'
        },
        {
            title: 'No-limit',
            name: 'negative_permitted',
            data: 'negative_permitted',
            render: datatables.boolRenderer('negative_permitted')
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
        }
    ],

    _init: function() {
        this._createDataTables();
    },

    _createDataTables: function() {
        $('table.user-list').each(function(index, elem) {
            this._createDataTable($(elem));
        }.bind(this));
    },

    _getTableColumns: function(role) {
        return this.columns.filter(function(column) {
            switch (column.name) {
                case 'username':
                    return true;
                case 'email':
                    return role !== ROLE_API;
                case 'accounts':
                    return true;
                case 'active':
                    return role !== ROLE_API;
                case 'permissions':
                    return role === ROLE_API;
            }
        });
    },

    _createDataTable: function(elem) {
        var role = elem.attr("data-role");
        var columns = this._getTableColumns(role);
        datatables.create_table(elem, {
            columns: columns,
            ajax: function(data, callback, settings) {
                backend.getUsersByRole(role).then(function(users) {
                    callback({ data: users });
                });
            }
        }, {export_csv: true, small_table: true, fixed_header: false});
    }
};
