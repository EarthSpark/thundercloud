// -*- coding: utf-8 -*-
// Copyright © 2013-2016 SparkMeter, Inc.
// All Rights Reserved.
//

var backend = require('backend.js').backend;

/* exported init_datatable */
function create_table(table_id, dtable_args, opts) {
    var elem = $(table_id);
    // Check if this element is visible on this page
    if (!elem.length) {
        return null;
    }
    var defaults = {export_csv: false,
                    fixed_header: false,
                    double_header: false,
                    small_table: false};
    opts = $.extend({}, defaults, opts);

    if (opts.double_header) {
        // fix bug with double header tables where resizing doesn't work
        dtable_args.bAutoWidth = false;
        // move the sorting button to the top header row
        dtable_args.orderCellsTop = true;
    }

    if (opts.small_table) {
        // no pagination
        dtable_args.bPaginate = false;
        // no filtering
        dtable_args.bFilter = false;
        // no x of x info at the bottom
        dtable_args.bInfo = false;
    }

    if (opts.export_csv) {
        // The dom option controls which DOM elements should be rendered
        // L: Length changing input controla
        // B: the Button plugin (for export buttons)
        // f: Filtering,
        // r: pRocessing display element
        // t: the Table itself
        // i: Information summary
        // p: pagination control
        // See https://datatables.net/reference/option/dom for more information
        dtable_args.dom = 'Blfrtip';
        dtable_args.buttons = {
            buttons: [
                { extend: 'csv', text: '<i class="icon-download-alt"></i> Export current page (CSV)',
                  exportOptions: { columns: opts.export_columns || ':visible',
                                   modifier: { page: 'current' },
                                   orthogonal: 'type' } } ],
            dom: {
                container: { tag: 'li', className: null },
                buttonLiner: { tag: null }
            }
        };
        if (!dtable_args.bServerSide) {
            dtable_args.buttons.buttons.unshift(
                { extend: 'csv', text: '<i class="icon-download-alt"></i> Export all results (CSV)',
                  exportOptions: { columns: opts.export_columns || ':visible',
                                   orthogonal: 'type' } }
            );
        }
    }

    var table = elem.DataTable(dtable_args);

    if (opts.export_csv) {
        var exportMenu = $(table.table().node()).parents('.box').find('#export-menu');
        table.buttons().containers().appendTo(exportMenu);
    }

    // Override width style for table, so that the columns can be resized
    table.table().node().style.width = "100%";

    if (table.context.length === 0) {
        return table;
    }

    if (opts.fixed_header) {
        new $.fn.dataTable.FixedHeader(table);
    }

    /*
     * This is a custom ordering plugin for the "age-num" type that places NaN/empty values after valid
     * numbers rather than before. The `-pre` suffix indicates that this is a datatables deformatter,
     * and, as such, it will only be executed once per datum.
     * (see https://datatables.net/manual/plug-ins/sorting )
     */
    $.fn.dataTable.ext.type.order['age-num-pre'] = function(data) {
        if (data === "" || isNaN(data)) {
            return Infinity;
        }
        return data;
    };

    return table;
}
exports.create_table = create_table;

function setup() {
    $.extend($.fn.dataTableExt.oStdClasses, {
        "sWrapper": "dataTables_wrapper form-inline"
    });

    $.fn.dataTable.Buttons.swfPath = '/static/swf/copy_csv_xls_pdf.swf';
}
exports.setup = setup;

function GroundDropDown() {
    this._init();
}

GroundDropDown.prototype = {
    _init: function() {
        this.groundChanged = null;
    },

    createTableFilter: function(table) {
        var tableData = table.data();
        var tableElement = table.table().node();

        if (tableData.length > 0) {
            var groundColumn = table.column('.ground');
            var tableClass = '.' + $(tableElement).closest('[data-list]').attr('data-list');

            // Filters on each dropdown change based on the value
            $('.select-filter' + tableClass).on('change', function() {
                var val = $.fn.dataTable.util.escapeRegex($(this).val());
                groundColumn.search(val ? '^' + val + '$' : '', true, false).draw();
            });
        }
    },

    populateGrounds: function(groundName) {
        if (groundName === 'null') {
            backend.getGrounds().done(function(grounds) {
                $('.select-filter').html('<option value>All</option>');
                grounds.forEach(function(ground) {
                    return $('.select-filter').append("<option value=" + ground.name + " serial=" + ground.serial + ">" + ground.name + "</option>");
                });
                if (this.callbackGroundsLoaded) {
                    this.callbackGroundsLoaded(grounds);
                }
            }.bind(this));
        } else {
            if (this.callbackGroundsLoaded) {
                this.callbackGroundsLoaded(null);
            }
        }
    }
};

exports.GroundDropDown = GroundDropDown;

function boolRenderer(attr) {
    return function(data, type, row) {
        if (row[attr] === true) {
            return 'Yes';
        } else {
            return 'No';
        }
    };
}

exports.boolRenderer = boolRenderer;

function getTableElement(table) {
    return $(table.table().node());
}
exports.getTableElement = getTableElement;

function onActiveTogggled(event) {
    var target = $(event.target);
    var group = target.parents("#active-group");

    // 1) Remove selection of all labels
    group
        .find('label')
        .removeClass('btn-default btn-info');

    // 2) Select the clicked label
    target
        .parent()
        .addClass('btn-info')
        .addClass('active');

    // 3) Add not-selected items
    group
        .find('label:not(".btn-info")')
        .addClass('btn-default');

    // 4) Search the datatables output
    var table = event.data.table;
    var value = target.val();
    table.column('meter_active:name')
        .search(value.toString())
        .draw();
}

exports.onActiveTogggled = onActiveTogggled;
