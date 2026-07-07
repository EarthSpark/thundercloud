// -*- coding: utf-8 -*-
// Copyright © 2013-2018 SparkMeter, Inc.
// All Rights Reserved.
//

var backend = require('backend.js').backend;
var base = require('base.js');
var datatables = require('datatables.js');

function TariffList() {
    this._init();
}

exports.TariffList = TariffList;

TariffList.prototype = {
    columns: [
        {
            name: 'name',
            render: function(data, type, row) {
                if (type === 'display') {
                    return base.linkify(
                        "/tariff/" + row.id + "/", row.name,
                        {'data-name': row.name}
                    );
                } else {
                    return row.name;
                }
            }
        },
        {
            name: 'load_limit',
            render: function(data, type, row) {
                return row.formatLoadLimit();
            }
        },
        {
            name: 'plan',
            render: function(data, type, row) {
                return row.formatPlan();
            }

        },
        {
            name: 'rate',
            render: function(data, type, row) {
                return row.formatRate();
            }

        },
        {
            name: 'tou_pricing',
            render: function(data, type, row) {
                return row.formatTOU();
            }
        },
        {
            name: 'daily_energy_limit',
            render: function(data, type, row) {
                return row.formatDailyEnergyLimit();
            }
        }
    ],

    _init: function() {
        this._createDataTables();
    },

    _createDataTables: function() {
        $('table.tariff-list').each(function(index, elem) {
            this._createDataTable($(elem));
        }.bind(this));
    },

    _createDataTable: function(elem) {
        datatables.create_table(elem, {
            columns: this.columns,
            ajax: function(data, callback, settings) {
                backend.getTariffs().then(function(tariffs) {
                    callback({ data: tariffs });
                });
            }
        }, {export_csv: true, small_table: true, fixed_header: false});
    }
};
