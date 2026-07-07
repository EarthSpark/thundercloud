// -*- coding: utf-8 -*-
// Copyright © 2013-2018 SparkMeter, Inc.
// All Rights Reserved.
//

/* global vg */

var backend = require('backend.js').backend;
var location = require('location.js');

function tableRow(columns, header) {
    var row = 'td';
    if (header === true) {
        row = 'th';
    }
    var html = '<tr>' + columns.map(function(e) {
        return '<' + row + '>' + e + '</' + row + '>';
    }).join('') + '</tr>';
    return html;
}

function createHourPeriods(defaultValue) {
    var hourPeriods = [];
    for (var i = 0; i <= 23; i++) {
        var period = {time: i};
        if (defaultValue !== undefined) {
            period.value = defaultValue;
        }
        hourPeriods.push(period);
    }
    return hourPeriods;
}

function parseLocation(pattern) {
    return pattern.exec(location.href)[1];
}

function TariffView() {
    this._init();
}

exports.TariffView = TariffView;

TariffView.prototype = {
    _init: function() {
        this.id = parseLocation(/\/tariff\/(.*)\/$/gm);
        backend.getTariff(this.id).done(this._loadTariff.bind(this));
    },

    _loadTariff: function(tariff) {
        this.tariff = tariff;
        this._updateView();
    },

    _updateView: function() {
        this._updateName();
        this._updateWarningOnLowBalance();
        this._updateCycleStartDay();
        this._updateLoadLimit();
        this._updatePlan();
        this._updateRate();
        this._updateTOUpricing();
        this._updateDailyLoadLimit();

        // FIXME: Breadcrumb and toolbar buttons flash while reloading the page
        $('.tariff-details').removeClass('hidden');
    },

    _updateDailyLoadLimit: function() {
        if (!this.tariff.daily_energy_limit_enabled) {
            $('dd.tariff-daily-energy-limit').text('Disabled');
            $('dd.tariff-daily-energy-limit-reset-hour').text('N/A');
            $('dd.tariff-daily-energy-limit-value').text('N/A');
            return;
        }

        $('dd.tariff-daily-energy-limit').text('Enabled');
        $('dd.tariff-daily-energy-limit-reset-hour').text(
            this.tariff.daily_energy_limit_reset_hour.toString().padStart(2, '0') + ":00"
        );
        $('dd.tariff-daily-energy-limit-value').text(this.tariff.daily_energy_limit_value);
    },

    _updateName: function() {
        $('.tariff-name').text(this.tariff.name);
    },

    _updateWarningOnLowBalance: function() {
        $('.tariff-warning-on-low-balance').text(this.tariff.low_balance_threshold || 'Off');
    },

    _updateCycleStartDay: function() {
        $('.tariff-cycle-start-day-of-month').text(this.tariff.cycle_start_day_of_month);
    },

    _updateLoadLimit: function() {
        var hourPeriods;
        var loadLimitType;
        if (this.tariff.load_limit_type === 'flat') {
            loadLimitType = 'Flat';
            hourPeriods = createHourPeriods(this.tariff.flat_load_limit);
            $('.tariff-load-limit').text(this.tariff.formatLoadLimit());
        } if (this.tariff.load_limit_type === 'scheduled') {
            loadLimitType = 'Scheduled';
            hourPeriods = createHourPeriods();
            hourPeriods.forEach(function(hourPeriod, hour) {
                var period = this.tariff.findLoadLimitPeriod(hour);
                if (period !== undefined) {
                    hourPeriod.value = parseFloat(period.value);
                }
            }.bind(this));

            this._renderDetailsTable({
                element: $('dd.tariff-load-limit'),
                header: ['Period start', 'Period end', 'Limit in watts'],
                rows: this.tariff.load_limits,
                rowFn: function(row) {
                    return [row.start, row.end, row.value];
                }
            });
        }

        var spec = this._getVegaScheduledLoadLimitOptions();
        spec.data[0].values = hourPeriods;
        vg.parse.spec(spec, function(chart) {
            chart({el: '.load-limits-graph'})
            // .on("mouseover", function(event, item) {
            //     console.log(item.datum.data.value);
            // })
                .renderer('svg')
                .update();
        });

        $('.tariff-load-limit-type').text(loadLimitType);
    },

    _updatePlan: function() {
        var planPrice = 'N/A';
        var planFixedFee = 'N/A';
        var planDuration = 'N/A';
        if (this.tariff.plan_enabled) {
            planPrice = this.tariff.plan_price;
            planFixedFee = this.tariff.plan_fixed_fee;
            planDuration = this.tariff.plan_duration_span + ' ' +
                (this.tariff.plan_duration_unit === 'd' ? 'day' : 'month');
        }
        $('.tariff-plan-price').text(planPrice);
        $('.tariff-plan-fixed-fee').text(planFixedFee);
        $('.tariff-plan-duration').text(planDuration);
    },

    _updateRate: function() {
        var tariffType;
        if (this.tariff.tariff_type === 'blockrate') {
            $('.tariff-flatrate').hide();
            this._renderDetailsTable({
                element: $('dd.tariff-blockrates'),
                header: [
                    'Min<br/>total energy (kWh)',
                    'Max<br/>total energy (kWh)',
                    $("meta[itemprop='config-currency']").attr("content") + '<br/>per KWH</th>'
                ],
                rows: this.tariff.blockrates,
                rowFn: function(row) {
                    return [row.lower, row.upper, row.value];
                }
            });
            tariffType = 'Blockrate';
        } else {
            $('dt.tariff-blockrates').hide();
            $('dd.tariff-flatrate').text(this.tariff.flat_rate);
            tariffType = 'Flat';
        }
        $('dd.tariff-type').text(tariffType);
    },

    _updateTOUpricing: function() {
        if (!this.tariff.tou_enabled) {
            $('dd.tariff-tou-periods').text('Disabled');
            return;
        }

        this._renderDetailsTable({
            element: $('dd.tariff-tou-periods'),
            header: ['Period start', 'Period end', 'Pricing %'],
            rows: this.tariff.tous,
            rowFn: function(row) {
                return [row.start, row.end, row.value];
            }
        });

        var hourPeriods = createHourPeriods(100);
        hourPeriods.forEach(function(hourPeriod, hour) {
            var period = this.tariff.findTouPeriod(hour);
            if (period !== undefined) {
                hourPeriod.value = parseFloat(period.value);
            }
        }.bind(this));

        var spec = this._getVegaTOUOptions();
        spec.data[0].values = hourPeriods;
        vg.parse.spec(spec, function(chart) {
            chart({el: '.tou-graph'})
            // .on("mouseover", function(event, item) {
            //     console.log(item.datum.data.value);
            // })
                .renderer('svg')
                .update();
        });

        $('.tariff-pricing-period').removeClass('hidden');
    },

    _renderDetailsTable: function(o) {
        var html = '<table class="tariff-details-table">' +
            tableRow(o.header, true) +
            '</table>';
        var table = o.element
            .append(html)
            .find('table');
        o.rows
            .map(o.rowFn)
            .map(tableRow)
            .map(function(row) {
                table.append(row);
            });
    },

    _getVegaTOUOptions: function() {
        return {
            width: 650,
            height: 200,
            padding: {top: 10, left: 60, bottom: 45, right: 10},
            data: [{name: "table", values: []}],
            scales: [{
                name: "x",
                range: "width",
                domain: [0, 24]
            }, {
                name: "y",
                range: "height",
                max: "100",
                domain: {data: "table", field: "data.value"}
            }],
            axes: [
                {type: "x", scale: "x", title: "Time of day (local time)"},
                {type: "y", scale: "y", titleOffset: 55, title: "TOU Modifier (%)"}
            ],
            marks: [{
                type: "rect",
                from: {data: "table"},
                properties: {
                    enter: {
                        x: {scale: "x", field: "data.time"},
                        width: {scale: "x", value: 1, offset: 2},
                        y: {scale: "y", field: "data.value"},
                        y2: {scale: "y", value: 0}
                    },
                    update: {
                        fill: {value: "steelblue"}
                    },
                    hover: {
                        fill: {value: "lightblue"}
                    }
                }
            }]
        };
    },

    _getVegaScheduledLoadLimitOptions: function() {
        return {
            width: 650,
            height: 200,
            padding: {top: 10, left: 60, bottom: 45, right: 10},
            data: [{name: "table", values: []}],
            scales: [{
                name: "x",
                range: "width",
                domain: [0, 24]
            }, {
                name: "y",
                range: "height",
                domain: {data: "table", field: "data.value"}
            }],
            axes: [
                {type: "x", scale: "x", title: "Time of day (local time)"},
                {type: "y", scale: "y", titleOffset: 55, title: "Load limit (W)"}
            ],
            marks: [{
                type: "rect",
                from: {data: "table"},
                properties: {
                    enter: {
                        x: {scale: "x", field: "data.time"},
                        width: {scale: "x", value: 1, offset: 2},
                        y: {scale: "y", field: "data.value"},
                        y2: {scale: "y", value: 0}
                    },
                    update: {
                        fill: {value: "steelblue"}
                    },
                    hover: {
                        fill: {value: "lightblue"}
                    }
                }
            }]
        };
    }

};
