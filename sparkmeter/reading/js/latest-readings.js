// Copyright © 2013-2017 SparkMeter, Inc.
// All Rights Reserved.
//
/*global tlite*/

var datatables = require('datatables.js');
var backend = require('backend.js').backend;
var base = require('base.js');
var MeterUtils = require('meter/js/meter-utils.js');
var DateUtils = require('dateutils.js');

function LatestReadings() {
    this._init();
}

tlite(function(el) {
    if (el.classList.contains("tooltipped")) {
        return {grav: 's'};
    } else {
        return false;
    }
});

exports.LatestReadings = LatestReadings;

function formatDecimalPlaces(value, places) {
    if (value === "" || value === null || value === undefined) {
        return "";
    }
    var number = Number(value);
    if (isNaN(number)) {
        return value;
    }
    return number.toFixed(places);
}

LatestReadings.prototype = {
    heartbeat_seconds: 900, // 15 min default
    refresh_interval: null,
    columns: [
        {
            title: "Meter Serial",
            data: "serial",
            type: "string",
            render: function(data, type, row) {
                return MeterUtils.formatMeterLink(row.serial);
            }
        },
        {
            title: "Customer Name",
            data: "customer_name",
            type: "string"
        },
        {
            title: "Customer Code",
            data: "customer_code",
            type: "string"

        },
        {
            title: "State",
            data: "state",
            type: "string"
        },
        {
            title: "Frequency (Hz)",
            data: "frequency",
            type: "num",
            render: function(data, type) {
                if (type === "display") {
                    return formatDecimalPlaces(data, 2);
                }
                return data;
            }
        },
        {
            title: "Avg Voltage (V)",
            data: "voltage_avg",
            type: "num",
            render: function(data, type) {
                if (type === "display") {
                    return formatDecimalPlaces(data, 2);
                }
                return data;
            }
        },
        {
            title: "Avg Current (A)",
            data: "current_avg",
            type: "num",
            render: function(data, type) {
                if (type === "display") {
                    return formatDecimalPlaces(data, 3);
                }
                return data;
            }
        },
        {
            title: "True Power (W)",
            data: "true_power_avg",
            type: "num"
        },
        {
            title: "Energy (kWh)",
            data: "energy",
            type: "num"
        },
        {
            title: "Uptime (s)",
            data: "uptime",
            type: "num"
        },
        {
            title: "Power Limit (W)",
            data: "user_power_limit",
            type: "num"
        },
        {
            title: "Age (s)",
            name: "age",
            type: "age-num",
            data: "heartbeat_end",
            render: function(data, type, row) {
                var age = (DateUtils.utcnow() - DateUtils.astimestamp(row.heartbeat_end));
                if (isNaN(age)) {
                    age = "";
                }
                return age;
            }
        },
        {
            title: "Address",
            data: "address",
            type: "string"
        },
        {
            title: "Ground",
            data: "ground_name",
            className: "ground",
            type: "string"
        }
    ],

    // this is called in the html page once the dom is loaded
    _init: function() {
        var groundName = base.getMetaItemProps('ground');

        this.load_datatable();
        this._groundDropDown = new datatables.GroundDropDown();
        this._groundDropDown.populateGrounds(groundName);
        $("#Color").change(this.toggle_color.bind(this));
        $("#Auto-refresh").change(this.toggle_auto_refresh.bind(this));
    },

    toggle_auto_refresh: function(event) {
        if ($(event.target).is(':checked')) {
            this.enable_auto_refresh();
        } else {
            this.disable_auto_refresh();
        }
    },

    enable_auto_refresh: function() {
        this.refresh_interval = setInterval(this.update.bind(this), 10000);
    },

    disable_auto_refresh: function() {
        this.refresh_interval = clearInterval(this.refresh_interval);
    },

    _formatUptimeTooltip: function(uptime, heartbeat_end) {
        if (uptime === "" && heartbeat_end === "") {
            return "";
        }
        var boot_time = DateUtils.astimestamp(heartbeat_end) - uptime;
        var run_time = DateUtils.formatDelta(uptime);
        var text = '';
        text += "Boot time: " + DateUtils.formatDate(new Date(boot_time * 1000)) + "<br>";
        text += "Run time: " + run_time;
        return text;
    },

    _formatAgeTooltip: function(heartbeat_end) {
        if (heartbeat_end === "") {
            return "";
        }
        var age_seconds = DateUtils.utcnow() - DateUtils.astimestamp(heartbeat_end);
        var text = '';
        text += "Received: " + DateUtils.formatDate(new Date(heartbeat_end + "+00:00")) + "<br>";
        text += DateUtils.formatDelta(age_seconds) + "<br>";
        text += parseInt(age_seconds / this.heartbeat_seconds, 10) + " heartbeat(s) ago.";
        return text;
    },

    _formatTooltipForField: function(field, row) {
        var text = '';
        switch (field) {
            /* 5th column */
            case 'voltage_avg': {
                text += "Min: " + row.voltage_min + "<br>";
                text += "Max: " + row.voltage_max + "<br>";
                break;
            }
            /* 6th column */
            case 'current_avg': {
                text += "Min: " + row.current_min + "<br>";
                text += "Max: " + row.current_max + "<br>";
                break;
            }
            /* 9th column */
            case 'uptime': {
                text += this._formatUptimeTooltip(row.uptime, row.heartbeat_end);
                break;
            }
            /* 11th column */
            case 'heartbeat_end': {
                text += this._formatAgeTooltip(row.heartbeat_end);
                break;
            }
        }
        return text;
    },

    createdCell: function(td, cellData, rowData, row, col) {
        var field_name = this.table.column(col).dataSrc();
        td.setAttribute("data-tlite", this._formatTooltipForField(field_name, rowData));
        td.classList.add("tooltipped");
        td.classList.add(field_name);
    },

    createdRow: function(row, data, index) {
        var age = DateUtils.utcnow() - DateUtils.astimestamp(data.heartbeat_end);
        this.color_row(row, age);
        row.firstElementChild.innerHTML = MeterUtils.formatMeterLink(data.serial);
    },

    load_datatable: function() {
        var tableElement = $('table#latestreadings');
        var table;

        $(tableElement).removeClass('table-striped table-hover');
        table = datatables.create_table(tableElement, {
            ajax: function(data, callback, settings) {
                backend.getLatestReadings().then(function(response) {
                    this.heartbeat_seconds = response.heartbeat_seconds;
                    callback({ data: response.readings });
                }.bind(this));
            },
            deferRender: true,
            fixedHeader: false,
            bPaginate: true,
            iDisplayLength: 100,
            columns: this.columns,
            bAutoWidth: false,
            columnDefs: [
                {
                    targets: [5, 6, 9, 11],
                    createdCell: this.createdCell.bind(this)
                }
            ],
            createdRow: this.createdRow.bind(this),
            initComplete: function() {
                this._groundDropDown.createTableFilter(table);
            }.bind(this)
        });

        // don't show an alert every 10 seconds if the backend is down.
        $.fn.dataTable.ext.errMode = 'throw';

        this.enable_auto_refresh();
        this.table = table;
    },

    update: function() {
        this.table.ajax.reload(null, false);
    },

    toggle_color: function(event) {
        if ($(event.target).is(':checked')) {
            // hover and striping interfere with coloring
            $("tbody").parent('table').removeClass('table-striped table-hover');
            $("tbody tr").each(function(i, row) {
                var $row = $(row);
                var age = $row.children(".heartbeat_end").text();
                this.color_row($row, age);
            }.bind(this));
        } else {
            $("tbody").parent('table').addClass('table-striped table-hover');
            this.remove_colors();
        }
    },

    remove_colors: function() {
        $("tr").removeClass('heartbeat-never heartbeat-current heartbeat-day-old heartbeat-hour-old heartbeat-last heartbeat-lost');
    },

    color_row: function(row, age) {
        // clear the previous color
        row.classList.remove(['heartbeat-never', 'heartbeat-current', 'heartbeat-day-old', 'heartbeat-hour-old', 'heartbeat-last', 'heartbeat-lost']);
        if (age === "" || isNaN(age)) {
            // Black: never seen
            row.classList.add('heartbeat-never');
        } else if (age < this.heartbeat_seconds) {
            // Green: within the current heartbeat period
            row.classList.add('heartbeat-current');
        } else if (age > 86400) {
            // Grey: not seen for more than one day
            row.classList.add('heartbeat-day-old');
        } else if (age > 3600) {
            // Red: not seen for more than one hour
            row.classList.add('heartbeat-hour-old');
        } else if (age < this.heartbeat_seconds * 2) {
            // Pale Green: within the last heartbeat period (no heartbeats missed yet)
            row.classList.add('heartbeat-last');
        } else {
            // Yellow: 1 heartbeat lost or more (at least 2 periods behind)
            row.classList.add('heartbeat-lost');
        }
    }
};
