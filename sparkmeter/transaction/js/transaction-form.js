// -*- coding: utf-8 -*-
// Copyright © 2013-2016 SparkMeter, Inc.
// All Rights Reserved.
//

var base = require('base.js');

function submit_form() {
    $('#transaction_confirm').prop('disabled', true);
    $('.goback').prop('disabled', true);
    $('.modal-body p').toggle();
    $('#transaction_form').submit();
}

function show_transaction_confirm() {
    $('#transaction_button').prop('disabled', true);
    $('#modal_transaction_confirm').modal('show');
}

function enable_transaction_button() {
    $('#transaction_button').prop('disabled', false);
}

function transaction_form() {
    function calculate() {
        var amount = parseFloat($('#amount').val()) || 0.0;
        var account_name = $('#account option:selected').text() || $('#account_name').val();
        $('#account_name').html(account_name);
        $('#total_display').val(amount);
        $('#transaction_amt').html(base.format_currency(amount));

        var acct_type = $('#acct_type option:selected');
        $('#acct_type_display').html(acct_type.text());
        var source_name = $('#source option:selected');
        $('#source_name').html(source_name.text());

        // enable/disable the make payment button depending on the source selected.
        if (source_name.val() === "__None") {
            $('#transaction_button').prop('disabled', true);
        } else {
            $('#transaction_button').prop('disabled', false);
        }
    }

    $('input').keyup(calculate);
    $('select').change(calculate);
    $('#acct_type').change(calculate);
    $('#source').change(calculate);
    calculate();
    $('#transaction_confirm').click(submit_form);
    $('#transaction_button').click(show_transaction_confirm);
    $('.goback').click(enable_transaction_button);
    $('#modal_transaction_confirm').click(enable_transaction_button);
}

exports.transaction_form = transaction_form;

function TransactionTransferForm() {
    this._init();
}

TransactionTransferForm.prototype = {
    _init: function() {
        $('#transaction_button').click(this._onTransactionButtonClicked.bind(this));
        $('#transaction_confirm').click(this._onTransactionConfirmClicked.bind(this));
        $('#acct_type').change(this._onAccountTypeChange.bind(this));
        $('#source').change(this._onSourceChange.bind(this));
        $('input').keyup(this._onInputKeyUp.bind(this));
        $('.goback').click(this._onGoBackClicked.bind(this));

        this._updateForm();
    },

    _calculateMarkup: function(amount) {
        var markup = parseFloat($('#markup').val()) || 0.0;
        return amount * markup;
    },

    _updateForm: function() {
        var amount = parseFloat($('#amount').val()) || 0.0;
        var acct_type = $('#acct_type option:selected');
        var source_name = $('#source option:selected');

        if (source_name.val() === "__None") {
            this._hideMarkupFields();
            this._transactionButtonDisabled(true);
        } else if (acct_type.val() === "debt" || source_name.text() === "bonus") {
            this._hideMarkupFields();
            this._transactionButtonDisabled(false);
        } else {
            this._showMarkupFields();
            this._transactionButtonDisabled(false);
        }

        if (source_name.text() !== 'bonus') {
            var markup = this._calculateMarkup(amount);
            amount += markup;
            $('#vendor_amt_display').val(markup);
            $('#total_display').val(amount);
        }
        $('#transaction_amt').html(base.format_currency(amount));
        $('#acct_type_display').html(acct_type.text());
        $('#source_name').html(source_name.text());
    },

    _submitForm: function() {
        this._transactionButtonDisabled(true);
        $('.goback').prop('disabled', true);
        $('.modal-body p').toggle();
        $('#transaction_form').submit();
    },

    _hideMarkupFields: function() {
        $('#markup').parents('.form-group').hide();
        $('#markup_hr').hide();
        $('#vendor_amt_display').parents('.form-group').hide();
        $('#total_display').parents('.form-group').hide();
    },

    _showMarkupFields: function() {
        $('#markup').parents('.form-group').show();
        $('#markup_hr').show();
        $('#vendor_amt_display').parents('.form-group').show();
        $('#total_display').parents('.form-group').show();
    },

    _transactionButtonDisabled: function(value) {
        $('#transaction_button').prop('disabled', value);
    },

    _showTransactionForm: function() {
        this._transactionButtonDisabled(true);
        $('#modal_transaction_confirm').modal('show');
    },

    // Callbacks

    _onAccountTypeChange: function() {
        this._updateForm();
    },

    _onSourceChange: function() {
        this._updateForm();
    },

    _onInputKeyUp: function() {
        this._updateForm();
    },

    _onTransactionConfirmClicked: function() {
        this._submitForm();
    },

    _onTransactionButtonClicked: function() {
        this._showTransactionForm();
    },

    _onGoBackClicked: function() {
        this._transactionButtonDisabled(false);
    }
};

exports.TransactionTransferForm = TransactionTransferForm;
