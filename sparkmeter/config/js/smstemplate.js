// -*- coding: utf-8 -*-
// Copyright © 2013-2016 SparkMeter, Inc.
// All Rights Reserved.
//
// SMS Template directive

/* global angular */

angular
    .module('sparkmeter.event.sms')
    .directive('smSmsTemplate', smSmsTemplate);

smSmsTemplate.$inject = ['SMSEventTypesService', 'Textcomplete'];

function smSmsTemplate(SMSEventTypesService, Textcomplete) {
    var d = this;
    _activate();
    return {
        link: link,
        require: 'ngModel',
        scope: {
            bindModel: '=ngModel'
        },
        template: template
    };

    function _activate() {
        SMSEventTypesService.query().then(function(eventTypes) {
            d.eventTypes = eventTypes;
        });
    }

    function _listKeywords(scope, completionType) {
        var eventType = _getEventType(scope, completionType);
        return d.eventTypes.getKeywordsForEventType(eventType);
    }

    function ngModelUpdated(ngModel, element, attrs, value) {
        value = value || "";
        var valid = value.length > 0;
        var tooLong = value.length > d.maxCharacters;
        ngModel.$setValidity("required", valid);

        // Update length node
        var eLengthSpan = element.find('p:nth(0) span');
        eLengthSpan.text(value.length);
        eLengthSpan.css('color', tooLong ? 'red' : '');
        eLengthSpan.css('font-weight', tooLong ? 'bold' : '');

        // Update element visibility,
        // - required validation, cannot be empty
        // - show character length box, only then there is content in the
        //   textarea itself, eg, hide if empty.
        var eLength = element.find('p:nth(0)');
        var eRequired = element.find('p:nth(1)');
        if (valid) {
            eRequired.hide();
            eLength.show();
        } else {
            eRequired.show();
            eLength.hide();
        }
    }

    function _getEventType(scope, completionType) {
        var eventType;
        if (completionType === 'alert') {
            eventType = scope.$parent.alert.event_type;
        } else {
            eventType = completionType;
        }
        return eventType;
    }

    function _updateHelpLink(element, eventType) {
        var a = element.find('a');
        a.attr('href', 'sms-template-help?event_type=' + eventType);
    }

    function _initializeTextcomplete(scope, textarea, completionType) {
        var textcomplete = new Textcomplete(textarea, [{
            match: /\B{([\-+\w]*)$/,
            search: function(term, callback) {
                var keywords = _listKeywords(scope, completionType);
                callback($.map(keywords, function(kw) {
                    return kw.name.indexOf(term) === 0 ? kw : null;
                }));
            },
            template: function(value) {
                return value.name;
            },
            replace: function(value) {
                return '{' + value.name + '}';
            },
            index: 1,
            maxCount: 30
        }]);

        $(textcomplete).on({
            'textComplete:select': function(e, value) {
                scope.$apply(function() {
                    textarea.trigger('input');
                });
            },
            'textComplete:show': function(e) {
                $(this).data('autocompleting', true);
            },
            'textComplete:hide': function(e) {
                $(this).data('autocompleting', false);
            }
        });
    }

    function link(scope, element, attrs, ngModel) {
        var eventType = _getEventType(scope, attrs.completionType);
        _updateHelpLink(element, eventType);

        scope.$watch(function() {
            return ngModel.$modelValue;
        }, function(value) {
            ngModelUpdated(ngModel, element, attrs, value);
        });

        var textarea = element.find('textarea');
        _initializeTextcomplete(scope, textarea, attrs.completionType);
    }

    function template(e, attrs) {
        d.maxCharacters = parseInt(attrs.maxCharacters || "160", 10);
        d.rows = parseInt(attrs.rows || "4", 10);
        var tmpl = '<textarea class="form-control" ' +
            'name="' + attrs.name + '" ' +
            'rows="' + d.rows + '"' +
            'style="resize: none"' +
            'ng-required="true" ' +
            'ng-model="bindModel">' +
            '</textarea>';

        if (attrs.completionType !== 'message') {
            // Question mark button for template documentation
            tmpl += '<a target="_blank" type="submit" class="btn btn-info">' +
                '<i class="icon-question-sign pull-left clear-right"></i>' +
                '</a>';
        }

        // Number of characters used in the template box
        tmpl += '<p class="pull-right"><span></span> / ' + d.maxCharacters + ' characters.</p>';

        // Validation message if the template is empty
        tmpl += '<p class="help-block">Template cannot be empty.</p>';
        return tmpl;
    }
}
