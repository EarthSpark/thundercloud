// -*- coding: utf-8 -*-
// Copyright © 2013-2017 SparkMeter, Inc.
// All Rights Reserved.
//

var backend = require('backend.js').backend;
var datatables = require('datatables.js');

function MeterList() {
    this._init();
}

exports.MeterList = MeterList;

MeterList.prototype = {
    columns: [
        {
            name: 'name',
            data: 'name',
            type: 'string'
        },
        {
            name: 'phase_count',
            data: 'phase_count',
            type: 'num'
        },
        {
            name: 'continuous_limit',
            data: 'continuous_limit',
            type: 'num'
        },
        {
            name: 'inrush_limit',
            data: 'inrush_limit',
            type: 'num'
        },
        {
            name: 'count',
            data: 'count',
            type: 'num'
        }
    ],

    _init: function() {
        this._createDataTable();
    },

    _createDataTable: function() {
        var elem = $('table.meter-list')[0];
        datatables.create_table($(elem), {
            columns: this.columns,
            ajax: function(data, callback, settings) {
                backend.getMeterModels().then(function(models) {
                    callback({ data: models });
                });
            },
            bPaginate: false,
            bInfo: false,
            order: [[2, 'asc'], [3, 'asc']]
        }, {
            export_csv: false,
            small_table: false,
            fixed_header: false
        });
    }
};
