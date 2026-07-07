// -*- coding: utf-8 -*-
// Copyright © 2013-2016 SparkMeter, Inc.
// All Rights Reserved.
//
// SMS Event Type handling

/* global angular */

angular
    .module('sparkmeter.event.sms')
    .factory('SMSEventTypesService', SMSEventTypesService);

SMSEventTypesService.$inject = ['CrudClientService', '$q'];

function SMSEventTypesService(CrudClientService, $q) {
    var svc = this;
    svc.data = null;
    _activate();

    function _activate() {
        svc.client = new CrudClientService("/event/event-types");
    }

    svc.getKeywordsForEventType = function getKeywordsForEventType(eventType) {
        if (eventType === "message") {
            return [];
        }
        var item = svc.data.find(function(i) {
            return i.value === eventType;
        });

        if (item === undefined) {
            throw Error("Invalid keyword type: " + eventType);
        }
        return item.keywords;
    };

    svc.query = function query() {
        var deferred = $q.defer();
        if (svc.data !== null) {
            deferred.resolve(svc);
        } else {
            svc.client.list().then(function(response) {
                svc.data = response.event_types;
                deferred.resolve(svc);
            });
        }
        return deferred.promise;
    };

    return svc;
}
