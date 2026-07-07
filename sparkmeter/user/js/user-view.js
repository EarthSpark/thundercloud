// -*- coding: utf-8 -*-
// Copyright © 2013-2018 SparkMeter, Inc.
// All Rights Reserved.
//

const backend = require('backend.js').backend;

function UserView() {
    this._init();
}

exports.UserView = UserView;

UserView.prototype = {
    _init: function() {
        $('button#reset-link').on('click', this._onConfirmResetCredentials.bind(this));
        this._window = window;
    },

    _onConfirmResetCredentials: function(event) {
        backend.resetCurrentCredentials().then(this._onCredentialsReset.bind(this));
    },

    _onCredentialsReset: function() {
        $("#modal-api-reset-credentials").modal('hide');
        this._window.location.reload();
    }
};
