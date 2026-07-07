// -*- coding: utf-8 -*-
// Copyright © 2013-2016 SparkMeter, Inc.
// All Rights Reserved.
//

function UserForm() {
    this._init();
}

exports.UserForm = UserForm;

UserForm.prototype = {
    _init: function() {
        $('.transaction_permission')
            .click(this._updateApiSalesAccounts.bind(this));
        this._updateElementDisabled(
            'select.api-sales-account',
            $('.transaction_permission').is(":checked"));

        $('#account_all_access')
            .click(this._updateAccounts.bind(this));
        this._updateElementDisabled(
            'select#accounts',
            $('#account_all_access').is(":checked"));
        $('#ground_all_access')
            .click(this._updateGrounds.bind(this));
        this._updateElementDisabled(
            'select#grounds',
            $('#ground_all_access').is(":checked"));
    },

    _updateAccounts: function(event) {
        this._updateElementDisabled('select#accounts', event.target.checked);
    },

    _updateApiSalesAccounts: function(event) {
        this._updateElementDisabled('select.api-sales-account', !event.target.checked);
    },

    _updateGrounds: function(event) {
        this._updateElementDisabled('select#grounds', event.target.checked);
    },

    _updateElementDisabled: function(selector, disabled) {
        var elem = $(selector);
        if (disabled) {
            elem.prop('disabled', true);
        } else {
            elem.removeProp("disabled");
        }
    }
};
