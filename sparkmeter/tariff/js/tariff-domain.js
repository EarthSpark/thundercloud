// -*- coding: utf-8 -*-
// Copyright © 2013-2018 SparkMeter, Inc.
// All Rights Reserved.

function findPeriod(periods, hour) {
    return periods.find(function(period) {
        var periodStart = parseInt(period.start.slice(0, 2), 10);
        var periodEnd = parseInt(period.end.slice(0, 2), 10);
        var matches;
        if (periodEnd === 24) {
            periodEnd = 0;
        }
        if (periodEnd > periodStart) {
            matches = hour >= periodStart && hour < periodEnd;
        } else {
            matches = hour >= periodStart || hour < periodEnd;
        }
        return matches;
    });
}

function Tariff() {
    this._init();
}

Tariff.prototype = {
    // This tariff is using a flat rate pricing
    TARIFF_TYPE_FLAT: 'flat',

    // This tariff is using blockrate pricing
    TARIFF_TYPE_BLOCKRATE: 'blockrate',

    // This tariff is using a flat load limit
    LOAD_LIMIT_TYPE_FLAT: 'flat',

    // This tariff is using a scheduled load limit
    LOAD_LIMIT_TYPE_SCHEDULED: 'scheduled',

    PLAN_DURATION_UNIT_DAY: 'd',

    PLAN_DURATION_UNIT_MONTH: 'm',

    _init: function() {
        this.id = null;
        this.name = '';
        this.blockrates = [];
        this.flat_rate = 0;
        this.id = null;
        this.flat_load_limit = 0;
        this.load_limits = [];
        this.load_limit_type = this.LOAD_LIMIT_TYPE_FLAT;
        this.plan_enabled = false;
        this.plan_price = 0;
        this.plan_fixed_fee = 0;
        this.plan_duration_span = 1;
        this.plan_duration_unit = this.PLAN_DURATION_UNIT_MONTH;
        this.cycle_start_day_of_month = 1;
        this.tariff_type = this.TARIFF_TYPE_FLAT;
        this.tou_enabled = false;
        this.tous = [];
        this.daily_energy_limit_enabled = false;
        this.daily_energy_limit_reset_hour = 0;
        this.daily_energy_limit_value = 0;
    },

    load: function(data) {
        this.id = data.id;
        this.name = data.name;
        this.blockrates = data.blockrates;
        this.flat_rate = data.flat_price;
        this.id = data.id;
        this.flat_load_limit = data.flat_load_limit;
        this.load_limits = data.load_limits;
        this.load_limit_type = data.load_limit_type;
        this.plan_enabled = data.plan_enabled;
        this.plan_price = data.plan_price;
        this.plan_fixed_fee = data.plan_fixed_fee;
        var plan_duration_parts;
        if (data.plan_duration) {
            plan_duration_parts = data.plan_duration.split(/(\d+)/).filter(Boolean);
        }
        this.plan_duration_span = plan_duration_parts ? parseInt(plan_duration_parts[0], 10) : undefined;
        this.plan_duration_unit = plan_duration_parts ? plan_duration_parts[1] : undefined;
        this.cycle_start_day_of_month = data.cycle_start_day_of_month;
        this.tariff_type = data.tariff_type;
        this.tou_enabled = data.tou_enabled;
        this.tous = data.tous;
        this.low_balance_threshold = data.low_balance_threshold;
        this.daily_energy_limit_enabled = data.daily_energy_limit_enabled;
        this.daily_energy_limit_reset_hour = data.daily_energy_limit_reset_hour;
        this.daily_energy_limit_value = data.daily_energy_limit_value;
        return this;
    },

    save: function() {
        return JSON.stringify(this, function(key, value) {
            if (typeof key === 'function') {
                return undefined;
            }
            return value;
        });
    },

    formatLoadLimit: function() {
        if (this.load_limit_type === this.LOAD_LIMIT_TYPE_FLAT) {
            return this.flat_load_limit.toString();
        } else if (this.load_limit_type === this.LOAD_LIMIT_TYPE_SCHEDULED) {
            var values = this.load_limits.map(function(loadLimit) {
                return loadLimit.value;
            });
            return '{min} to {max}'
                .replace('{min}', Math.min.apply(null, values))
                .replace('{max}', Math.max.apply(null, values));
        }
    },

    formatRate: function() {
        if (this.tariff_type === this.TARIFF_TYPE_FLAT) {
            return this.flat_rate.toString();
        } else if (this.tariff_type === this.TARIFF_TYPE_BLOCKRATE) {
            var values = this.blockrates.map(function(blockrate) {
                return blockrate.value;
            });
            return '{min} to {max}'
                .replace('{min}', Math.min.apply(null, values))
                .replace('{max}', Math.max.apply(null, values));
        }
    },

    formatTOU: function() {
        if (!this.tou_enabled) {
            return '----';
        }
        var values = this.tous.map(function(tou) {
            return tou.value;
        });
        // add 100 to the list so if only one modifier is set it
        // doesn't look like the normal is never used
        values.push(100);
        return '{min}% to {max}%'
            .replace('{min}', Math.min.apply(null, values))
            .replace('{max}', Math.max.apply(null, values));
    },

    formatDailyEnergyLimit: function() {
        if (!this.daily_energy_limit_enabled) {
            return '----';
        }
        return '{limit} kWh @ {hour}:00'
            .replace('{limit}', this.daily_energy_limit_value)
            .replace('{hour}', this.daily_energy_limit_reset_hour.toString().padStart(2, '0'));
    },

    formatPlan: function() {
        if (!this.plan_enabled) {
            return '----';
        }
        return '{span} {unit} for {plan_cost} {currency}'
            .replace('{span}', this.plan_duration_span)
            .replace('{unit}', this.plan_duration_unit === this.PLAN_DURATION_UNIT_DAY ? 'day' : 'month')
            .replace('{plan_cost}', this.plan_fixed_fee + this.plan_price)
            .replace('{currency}', $("meta[itemprop='config-currency']").attr('content'));
    },

    findLoadLimitPeriod: function(hour) {
        if (this.load_limit_type !== 'scheduled') {
            throw new Error("Load limit must be scheduled");
        }
        return findPeriod(this.load_limits, hour);
    },

    findTouPeriod: function(hour) {
        if (this.tou_enabled !== true) {
            throw new Error("TOU must be enabled");
        }
        return findPeriod(this.tous, hour);
    }
};

exports.Tariff = Tariff;
