// -*- coding: utf-8 -*-
// Copyright © 2013-2017 SparkMeter, Inc.
// All Rights Reserved.
//
// SMS Example renderer filter

/* global angular */

var base = require('base.js');

angular
    .module('sparkmeter.event.sms')
    .filter('templateExampleRenderer', SMSTemplateExampleRenderer);

SMSTemplateExampleRenderer.$inject = ['SMSEventTypesService'];

function SMSTemplateExampleRenderer(SMSEventTypesService) {
    var f = this;
    _activate();
    return filterFunc;

    function filterFunc(input, eventType) {
        if (input === undefined || input.length === 0) {
            return '';
        }
        var keywords = f.eventTypes.getKeywordsForEventType(eventType);
        keywords.forEach(function(keyword) {
            input = base.replaceAll(input, '{' + keyword.name + '}', keyword.example);
        });
        return input;
    }

    function _activate() {
        SMSEventTypesService.query().then(function(eventTypes) {
            f.eventTypes = eventTypes;
        });
    }
}
