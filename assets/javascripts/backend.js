// -*- coding: utf-8 -*-
// Copyright © 2013-2018 SparkMeter, Inc.
// All Rights Reserved.

var Tariff = require('tariff/js/tariff-domain.js').Tariff;

function BackendAPI() {
    this._init();
}

exports.BackendAPI = BackendAPI;

BackendAPI.prototype = {

    API_HEADER: 'Authentication-Token',

    _init: function() {
        this._authRetries = 0;
    },

    getToken: function() {
        var d = jQuery.Deferred();
        var token = localStorage.getItem('token');
        if (token !== null) {
            return d.resolve(token);
        }
        var options = {
            method: 'GET',
            url: '/user/token.json'
        };
        jQuery.ajax(options).done(function(response) {
            localStorage.setItem('token', response.token);
            this._authRetries = 0;
            d.resolve(response.token);
        });
        return d.promise();
    },

    _fetchAjax: function(options, deferred) {
        jQuery.ajax(options)
            .done(function(response) {
                return deferred.resolve(response);
            })
            .fail(function(response) {
                if (this._authRetries > 3) {
                    throw new Error("Error", response);
                } else {
                    localStorage.removeItem('token');
                    this._authRetries += 1;
                    this._fetch(options, deferred);
                }
            }.bind(this));
    },

    _fetch: function(options, deferred) {
        options.headers = options.headers || {};
        if (deferred === undefined) {
            deferred = jQuery.Deferred();
        }
        this.getToken().done(function(token) {
            options.headers[this.API_HEADER] = localStorage.getItem('token');
            this._fetchAjax(options, deferred);
        }.bind(this));
        return deferred.promise();
    },

    get: function(url) {
        return this._fetch({
            method: 'GET',
            url: '/api/v0' + url
        });
    },

    put: function(url, data) {
        return this._fetch({
            data: JSON.stringify(data),
            headers: {'Content-Type': 'application/json'},
            method: 'PUT',
            url: '/api/v0' + url
        });
    },

    listConfigParameters: function() {
        var d = jQuery.Deferred();
        this.get('/config/').done(function(response) {
            return d.resolve(response.parameters);
        });
        return d.promise();
    },

    saveConfigParameter: function(name, value) {
        return this.put('/config/' + name, {value: value});
    },

    getTariff: function(tariff_id) {
        var d = jQuery.Deferred();
        this.get('/tariff/' + tariff_id).done(function(response) {
            return d.resolve(new Tariff().load(response.tariff));
        });
        return d.promise();
    },

    getTariffs: function() {
        var d = jQuery.Deferred();
        this.get('/tariffs').done(function(response) {
            return d.resolve(response.tariffs.map(function(tariff) {
                return new Tariff().load(tariff);
            }));
        });
        return d.promise();
    },

    getUsersByRole: function(role) {
        var d = jQuery.Deferred();
        jQuery.ajax("/users.json?role=" + role)
            .done(function(response) {
                return d.resolve(response.users);
            });
        return d.promise();
    },

    getTransactions: function(datatableData) {
        var d = jQuery.Deferred();
        jQuery.ajax("transactions.json", {data: datatableData})
            .done(function(response) {
                return d.resolve({
                    data: response.transactions,
                    draw: response.draw,
                    recordsTotal: response.total,
                    recordsFiltered: response.total
                });
            });
        return d.promise();
    },

    getMessages: function(datatableData) {
        var d = jQuery.Deferred();
        jQuery.ajax("messages.json", {data: datatableData})
            .done(function(response) {
                return d.resolve({
                    data: response.messages,
                    draw: response.draw,
                    recordsTotal: response.total,
                    recordsFiltered: response.total
                });
            });
        return d.promise();
    },

    getLatestReadings: function() {
        var d = jQuery.Deferred();
        jQuery.ajax("latest.json")
            .done(function(response) {
                return d.resolve(response);
            });
        return d.promise();
    },

    getCustomerMeters: function() {
        var d = jQuery.Deferred();
        jQuery.ajax("/meter/meters.json?meter_type=customer")
            .done(function(response) {
                return d.resolve(response.meters);
            });
        return d.promise();
    },

    getTotalizerMeters: function() {
        var d = jQuery.Deferred();
        jQuery.ajax("/meter/meters.json?meter_type=totalizer")
            .done(function(response) {
                return d.resolve(response.meters);
            });
        return d.promise();
    },

    getMeterModels: function() {
        return this.get('/meters/models').then(function(response) { return response.models; });
    },

    getGrounds: function() {
        var d = jQuery.Deferred();
        jQuery.ajax("/user/grounds.json")
            .done(function(response) {
                return d.resolve(response.grounds);
            });
        return d.promise();
    },

    getSalesAccounts: function(page, accountType) {
        var base_url;
        switch (page) {
            case 'my':
                base_url = '/user/sales-account/';
                break;
            case 'user':
                base_url = 'sales-account/';
                break;
            case 'all':
                base_url = '/sales-account/';
                break;
            default:
                throw new Error("Unknown page: " + page);
        }
        var d = jQuery.Deferred();
        jQuery.ajax(base_url + accountType + ".json")
            .done(function(response) {
                return d.resolve(response.sales_accounts);
            });
        return d.promise();
    },

    resetCurrentCredentials: function() {
        return jQuery.ajax({
            type: "POST",
            url: "reset-credentials.json",
            contentType: "application/json; charset=utf-8",
            dataType: "json"
        });
    },

    verifyPhoneNumber: function() {
        return jQuery.ajax({
            type: "PUT",
            url: "verify-phone-number",
            dataType: "json"
        });
    },

    setMeterState: function(state) {
        return jQuery.ajax({
            type: "POST",
            url: "set-state",
            data: JSON.stringify({state: state}),
            contentType: "application/json; charset=utf-8",
            dataType: "json"
        });
    }
};

exports.backend = new BackendAPI();
