// -*- coding: utf-8 -*-
// Copyright © 2013-2018 SparkMeter, Inc.
// All Rights Reserved.
//

var backend = require('backend.js').backend;
var base = require('base.js');

function SettingsPage(fields) {
    this._init(fields);
}

exports.SettingsPage = SettingsPage;

SettingsPage.prototype = {

    _init: function(fields) {
        this._fields = fields || ['allow-negative-balance', 'debt-payback-percent', 'nominal-voltage'];
        this._parameters = {};
        this._statusUpdateHandlerId = null;
        this._form = $('form');
        backend.listConfigParameters().done(this._onParametersLoaded.bind(this));
    },

    _buildParameter: function(name, extra) {
        var parameter = this._parameters[name];
        var param = {
            label: parameter.label,
            name: name,
            tooltip: parameter.tooltip,
            value: parameter.value,
            value_type: parameter.value_type,
            validationError: false,
            validationMessage: ''
        };
        if (extra !== undefined) {
            for (var key in extra) {
                if (extra.hasOwnProperty(key)) {
                    param[key] = extra[key];
                }
            }
        }
        return param;
    },

    _readInput: function(input, param) {
        var value;
        var invalid = false;
        switch (param.value_type) {
            case 'bool':
                value = input.attr('value') === 'true';
                break;
            case 'percent':
                value = parseFloat(input.val());
                if (value < 0 || value > 100) {
                    invalid = true;
                    param.validationMessage = param.label + ' must be between 0 and 100';
                }
                value = Math.min(Math.max(value, 0.0), 100.0);
                if (isNaN(value)) {
                    invalid = true;
                    param.validationMessage = param.label + ' must be a number';
                }
                break;
            case 'voltage':
                value = parseFloat(input.val());
                if (value < 100 || value > 240) {
                    invalid = true;
                    param.validationMessage = param.label + ' must be between 100 and 240 volts';
                }
                value = Math.min(Math.max(value, 100.0), 240.0);
                if (isNaN(value)) {
                    invalid = true;
                    param.validationMessage = param.label + ' must be a number';
                }
                break;
            default:
                throw new Error('Unimplemented: ' + param.value_type);
        }
        // Wait for the validation phase to complete before passing final judgment
        if (invalid) {
            param.validationError = true;
        } else {
            param.validationError = false;
            param.validationMessage = '';
        }
        return value;
    },

    _createFieldFromTemplate: function(body, param, fieldType) {
        fieldType = fieldType || 'input';
        var template = body;
        template = base.replaceAll(template, '{name}', param.name);
        template = base.replaceAll(template, '{label}', param.label);
        template = base.replaceAll(template, '{tooltip}', param.tooltip);
        return this._form
            .append(template)
            .find(fieldType + '[name^=' + param.name + ']');
    },

    _createBooleanField: function(param, options) {
        var tmpl = '<div class="row">' +
            '<div class="form-group">' +
            '<label for="{name}-true" class="control-label col-md-2">{label}</label>' +
            '<div id="radio-group-{name}" class="btn-group  col-md-2" title="{tooltip}" data-toggle="buttons">' +
            '<label class="btn btn-primary">' +
            '<input type="radio" name="{name}" id="{name}-true" value="true">' + options.labels[0] +
            '</label>' +
            '<label class="btn btn-primary">' +
            '<input type="radio" name="{name}" id="{name}-false" value="false">' + options.labels[1] +
            '</label>' +
            '</div>' +
            '</div>' +
            '</div>';
        var field = this._createFieldFromTemplate(tmpl, param);
        field.filter('[value=true]')
            .attr('checked', param.value)
            .parent()
            .toggleClass('active', param.value);
        field.filter('[value=false]')
            .attr('checked', !param.value)
            .parent()
            .toggleClass('active', !param.value);
        field.on('change', param, this._onParameterChange.bind(this));
        return field;
    },

    _createPercentField: function(param) {
        var tmpl = '<div class="row">' +
            '<div class="form-group">' +
            '<label for="{name}" class="control-label col-md-2">{label}</label>' +
            '<div class="input-group col-md-2">' +
            '<input class="form-control"' +
            ' id="{name}"' +
            ' title="{tooltip}"' +
            ' name="{name}"' +
            ' type="text"/>' +
            '<span class="input-group-addon">%</span>' +
            '</div>' +
            '</div>' +
            '</div>';
        var field = this._createFieldFromTemplate(tmpl, param);
        field.val(param.value);
        field.on('input', param, this._onParameterChange.bind(this));
        return field;
    },

    _createListField: function(param, options) {
        var tmpl = '<div class="row">' +
            '<div class="form-group">' +
            '<label for="{name}" class="control-label col-md-2">{label}</label>' +
            '<div class="col-md-2">' +
            '<select class="form-control"' +
            ' id="{name}"' +
            ' title="{tooltip}"' +
            ' name="{name}">' +
            options.map(function(option) { return '<option value="' + option + '">' + option + ' Volts</option>'; }).join() +
            '</select>' +
            '</div>' +
            '</div>' +
            '</div>';
        var field = this._createFieldFromTemplate(tmpl, param, 'select');
        field.val(param.value);
        field.on('change', param, this._onParameterChange.bind(this));
        return field;
    },

    _createFormField: function(name, options) {
        var param = this._buildParameter(name);
        switch (param.value_type) {
            case 'bool':
                return this._createBooleanField(param, options);
            case 'percent':
                return this._createPercentField(param, options);
            case 'voltage':
                return this._createListField(param, [110, 120, 220, 230, 240]);
            default:
                throw new Error('Unimplemented: ' + param.value_type);
        }
    },

    _createSaveButton: function() {
        var html = '<div class="row">' +
            '<div id="#settingsFormSaveGroup" class="form-group">' +
            '<div class="col-sm-offset-2 col-sm-10">' +
            '<button class="btn btn-primary" id="save" ' +
            'type="submit" data-action="save">Save</button>' +
            '<span id="settingsFormValidationMessage" class="help-block"></div>' +
            '</div>' +
            '</div>' +
            '</div>';
        this._form.append(html);
        $('#save').on('click', this._onSaveClicked.bind(this));
    },

    _saveForm: function() {
        // Save all of the parameters one by one.
        // FIXME: Add a new backend API to save all parameters at once.
        var deferreds = [];
        for (var name in this._parameters) {
            if (this._parameters.hasOwnProperty(name) && this._fields.indexOf(name) > -1) {
                var value = this._parameters[name].value;
                deferreds.push(backend.saveConfigParameter(name, value));
            }
        }
        $.when.apply($, deferreds).done(this._onFormSaved.bind(this));
    },

    _applyValidation: function() {
        for (var name in this._parameters) {
            if (this._parameters.hasOwnProperty(name)) {
                var param = this._parameters[name];
                if (param.validationError) {
                    this._showValidationError(param.validationMessage);
                    return;
                }
            }
        }
        this._hideValidationError();
    },

    _showValidationError: function(message) {
        $('#save').prop('disabled', true);
        $('#settingsFormValidationMessage').text(message);
        $('#settingsFormValidationMessage').show();
        $('#settingsFormSaveGroup').addClass('has-error');
    },

    _hideValidationError: function() {
        $('#save').prop('disabled', false);
        $('#settingsFormValidationMessage').hide();
        $('#settingsFormValidationMessage').text('');
        $('#settingsFormSaveGroup').removeClass('has-error');
    },

    _validateResponses: function(responses) {
        var successes = responses.filter(function(response) {
            return response.status === 'success';
        });
        return responses.length === successes.length;
    },

    _onParametersLoaded: function(parameters) {
        this._parameters = parameters;
        if (this._fields.indexOf('allow-negative-balance') > -1) {
            this._createFormField('allow-negative-balance', {
                labels: ['Allow', 'Convert to Debt']
            });
        }
        if (this._fields.indexOf('debt-payback-percent') > -1) {
            this._createFormField('debt-payback-percent');
        }
        if (this._fields.indexOf('nominal-voltage') > -1) {
            this._createFormField('nominal-voltage');
        }
        this._createSaveButton();
        this._applyValidation();
    },

    _onParameterChange: function(event) {
        var input = $(event.target);
        var param = event.data;
        param.value = this._readInput(input, param);
        this._parameters[param.name] = param;
        this._applyValidation();
    },

    _onSaveClicked: function(event) {
        event.preventDefault();
        this._saveForm();
    },

    _onFormSaved: function() {
        var responses = Array.prototype.slice.call(arguments);
        if (this._validateResponses(responses)) {
            base.flash('Settings saved.', 'success', 5000);
        } else {
            base.flash('Failed to properly save settings.', 'danger', 5000);
        }
    }
};
