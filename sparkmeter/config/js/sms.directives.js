// -*- coding: utf-8 -*-
// Copyright © 2013-2016 SparkMeter, Inc.
// All Rights Reserved.
//
// SMS Application directives
// Our application with dependencies

/* global angular */

angular
    .module('sparkmeter.event.sms')
    .directive('smForceUppercase', smForceUppercase);

function smForceUppercase() {
    return {
        require: 'ngModel',
        link: link
    };

    function parseFunc(input) {
        if (input) {
            return input.toUpperCase();
        }
        return "";
    }

    function link(scope, element, attrs, modelCtrl) {
        modelCtrl.$parsers.push(parseFunc);
        // Always render the text as upper case, even if it's not
        element.css("text-transform", "uppercase");
    }
};
