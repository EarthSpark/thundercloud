// -*- coding: utf-8 -*-
// Copyright © 2013-2018 SparkMeter, Inc.
// All Rights Reserved.
//

var backend = require('backend.js').backend;
var base = require('base.js');
var datatables = require('datatables.js');
var MeterUtils = require('meter/js/meter-utils.js');

var STATE_OFF = 0;
var STATE_ON = 1;
var STATE_AUTO = 2;

function CustomerMeterList() {
    this._init();
}

exports.CustomerMeterList = CustomerMeterList;

CustomerMeterList.prototype = {
    columns: [
        {
            title: 'Serial',
            name: 'serial',
            data: 'meter_serial',
            type: 'string',
            render: function(data, type, row) {
                return MeterUtils.formatMeterLink(row.meter_serial);
            }
        },
        {
            title: 'Tariff Level',
            name: 'tariff_name',
            data: 'tariff_name',
            type: 'string'
        },
        {
            title: 'State',
            name: 'state',
            type: 'string',
            render: function(data, type, row) {
                if (type === 'display' || type === 'filter') {
                    var state_value = row.meter_state;
                    if (state_value === STATE_AUTO) {
                        if (row.tariff_plan_enabled && !row.meter_is_running_plan) {
                            state_value = STATE_OFF;
                        } else if (row.meter_plan_value <= 0 && row.meter_credit_value <= 0) {
                            state_value = STATE_OFF;
                        } else {
                            state_value = STATE_ON;
                        }
                    }

                    var txt = ["Off", "On"][state_value];
                    if (row.meter_state === STATE_AUTO) {
                        txt = 'Auto (' + txt + ')';
                    }
                    return txt;
                } else {
                    return row.meter_state;
                }
            }
        },
        {
            title: 'Customer Name',
            name: 'customer_name',
            data: 'customer_name',
            type: 'string'
        },
        {
            title: 'Customer Code',
            name: 'customer_code',
            data: 'customer_code',
            type: 'string'
        },
        {
            title: 'Phone Number',
            name: 'phone_number',
            type: 'string',
            render: function(data, type, row) {
                var value = row.customer_phone_number;
                if (type === 'display') {
                    value += ' ';
                    if (row.customer_phone_number_verified) {
                        value += '<i class="icon-ok icon-success"/>';
                    }
                } else if (type === 'filter') {
                    value = [value];
                    if (row.customer_phone_number) {
                        value.push('phone');
                    }
                }
                return value;
            }
        },
        {
            title: 'Verified',
            name: 'phone_number_verified',
            data: 'customer_phone_number_verified',
            type: 'string', visible: false
        },
        {
            title: 'Total Credit',
            name: 'total_credit',
            type: 'num-fmt',
            render: function(data, type, row) {
                return row.meter_plan_value + row.meter_credit_value;
            }
        },
        {
            title: 'Address',
            name: 'address',
            type: 'string',
            visible: false,
            render: function(data, type, row) {
                var parts = [];
                if (row.address_street1) parts.push(row.address_street1);
                if (row.address_street2) parts.push(row.address_street2);
                if (row.address_city) parts.push(row.address_city);
                if (row.address_state) parts.push(row.address_state);
                return parts.join(", ");
            }
        },
        {
            title: 'Coords',
            name: 'coords',
            data: 'address_coords',
            type: 'string'
        },
        {
            title: 'Tags',
            name: 'tags',
            sortable: false,
            type: 'string',
            visible: false,
            render: function(data, type, row) {
                var tags = row.meter_tags.split(",");
                tags.sort();
                if (type === 'display') {
                    return MeterUtils.formatMeterTags(tags);
                }
                // csv, filtering etc
                return tags.join(" ");
            }
        },
        {
            title: 'Active',
            name: 'meter_active',
            data: 'meter_active',
            type: 'boolean',
            visible: false
        },
        {
            title: 'Ground',
            name: 'ground_name',
            data: 'ground_name',
            type: 'string',
            className: 'ground'
        },
        {
            title: 'Details', name: 'details', type: 'string',
            render: function(data, type, row) {
                if (type === 'display') {
                    return ('<button class="btn btn-info detail-btn" data-action="view" data-toggle="collapse"' +
                        'data-target="' + row.id + '">View</button>');
                } else if (type === 'filter') {
                    /* Provide filter keywords so the user can search for 'processed etc */
                    var keywords = [];
                    if (row.address_street1) {
                        keywords.push('address_street1');
                    }
                    if (row.address_street2) {
                        keywords.push('address_street2');
                    }
                    if (row.address_city) {
                        keywords.push('address_city');
                    }
                    if (row.address_state) {
                        keywords.push('address_state');
                    }
                    if (row.address_coords) {
                        keywords.push('address_coords');
                    }
                    if (row.meter_credit_value) {
                        keywords.push('credit');
                    }
                    if (row.meter_debt_value) {
                        keywords.push('debt');
                    }
                    if (row.meter_plan_value) {
                        keywords.push('plan');
                    }
                    return keywords.join(' ');
                } else {
                    return '';
                }
            }
        },
        {
            title: 'Credit',
            name: 'credit',
            data: 'meter_credit_value',
            type: 'number',
            visible: false
        },
        {
            title: 'Debt',
            name: 'debt',
            data: 'meter_debt_value',
            type: 'number',
            visible: false
        },
        {
            title: 'Plan',
            name: 'plan',
            data: 'meter_plan_value',
            type: 'number',
            visible: false
        }
    ],

    _init: function() {
        var groundName = base.getMetaItemProps('ground');

        this._tables = this._createDataTable($('table.customer-meter-list'));
        this._groundDropDown = new datatables.GroundDropDown();
        this._groundDropDown.populateGrounds(groundName);
        this._listenEvents();
    },

    _toggleDetailsClicked: function(tr) {
        var row = this._tables.row(tr);
        if (row.child.isShown()) {
            row.child.hide();
            return tr.removeClass('shown');
        } else {
            row.child(this._renderDetails(row.data())).show();
            return tr.addClass('shown');
        }
    },

    _listenEvents: function() {
        var me = this;
        $('.customer-meter-list tbody')
            .on('click', '[data-toggle="collapse"]', function() {
                var tr = $(this).closest('tr');
                me._toggleDetailsClicked(tr);
            });
    },

    _createDataTable: function(elem) {
        var opts = {
            export_csv: true,
            fixed_header: false
        };

        opts.export_columns = [
            0, // serial
            1, // tariff
            2, // state
            3, // customer name
            4, // customer code
            5, // phone number
            6, // verified
            7, // total credit
            8, // address
            9, // coords
            10, // tags
            11, // active
            14, // credit
            15, // debt
            16 // plan
        ];

        var table = datatables.create_table(elem, {
            bPaginate: true,
            columns: this.columns,
            iDisplayLength: 100,
            oSearch: {
                bSmart: false,
                bRegex: true
            },
            language: {
                info: "Showing meters _START_ to _END_ (of a total of _TOTAL_)",
                infoEmpty: "Showing 0 meters (of a total of 0)",
                infoFiltered: ""
            },
            ajax: function(data, callback, settings) {
                backend.getCustomerMeters().then(function(meters) {
                    callback({ data: meters });
                });
            },
            initComplete: function() {
                this._groundDropDown.createTableFilter(table);
            }.bind(this)
        }, opts);

        table.column('meter_active:name').search('true');
        $(table.table().node())
            .parents(".box")
            .find("input[name=active]")
            .change({table: table}, datatables.onActiveTogggled.bind(this));

        return table;
    },

    _renderDetails: function(row) {
        var html = '';
        html += base.detailItems('Credit: ' + row.meter_credit_value);
        if (row.meter_debt_value) {
            html += base.detailItems('Debt: ' + row.meter_debt_value);
        }
        if (row.meter_plan_value) {
            html += base.detailItems('Plan: ' + row.meter_plan_value);
        }
        if (row.address_street1) {
            html += base.detailItems('Address: ' + row.address_street1 + ' ' + row.address_street2);
            html += base.detailItems('City: ' + row.address_city);
            html += base.detailItems('State: ' + row.address_state);
            html += base.detailItems('Coords: ' + row.address_coords);
        }

        if (row.meter_tags) {
            var tagArr = row.meter_tags.split(',');
            for (var i = 0; i < tagArr.length; ++i) {
                html += base.detailItems('Tag: ' + tagArr[i], 'tags');
            }
        }
        return html;
    }
};
