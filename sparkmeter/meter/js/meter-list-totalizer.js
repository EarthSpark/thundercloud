// -*- coding: utf-8 -*-
// Copyright © 2013-2018 SparkMeter, Inc.
// All Rights Reserved.
//

var base = require('base.js');
var backend = require('backend.js').backend;
var datatables = require('datatables.js');
var MeterUtils = require('meter/js/meter-utils.js');

function TotalizerMeterList() {
    this._init();
}

exports.TotalizerMeterList = TotalizerMeterList;

TotalizerMeterList.prototype = {
    columns: [
        {
            title: 'Serial',
            name: 'serial',
            data: 'meter_serial',
            type: 'string',
            render: function(data, type, row) {
                if (type === 'display') {
                    return MeterUtils.formatMeterLink(row.meter_serial);
                } else {
                    return row.meter_serial;
                }
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
            visible: true,
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
        }
    ],

    _init: function() {
        var groundName = base.getMetaItemProps('ground');

        this._tables = this._createDataTable($('table.totalizer-meter-list'));
        this._groundDropDown = new datatables.GroundDropDown();
        this._groundDropDown.populateGrounds(groundName);
    },

    _createDataTable: function(elem) {
        var opts = {
            export_csv: true,
            fixed_header: false
        };

        opts.export_columns = [0, 1, 2, 3, 4, 5];

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
                backend.getTotalizerMeters().then(function(meters) {
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
    }
};
