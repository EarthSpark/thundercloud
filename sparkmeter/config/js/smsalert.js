// -*- coding: utf-8 -*-
// Copyright © 2013-2016 SparkMeter, Inc.
// All Rights Reserved.
//
// Alert handling

/* global angular */

var base = require('base.js');

angular
    .module('sparkmeter.event.sms')
    .factory('SMSAlertsService', SMSAlertsService);

SMSAlertsService.$inject = ['CrudClientService', '$q'];

function SMSAlertsService(CrudClientService, $q) {
    var svc = this;
    _activate();

    function _activate() {
        svc.uiName = "SMS Alert";
        svc.createProp = "alert_id";
        svc.readProp = "alert";
        svc.listProp = "alerts";
        svc.templateUrl = 'sms-config-alert-modal.html';
        svc.client = new CrudClientService("/alert/config/smsalerts/:id");
        svc.read = svc.client.read.bind(svc.client);
        svc.remove = svc.client.remove.bind(svc.client);
        svc.update = svc.client.update.bind(svc.client);
        svc.list = svc.client.list.bind(svc.client);
    }

    function _showMessage(message) {
        base.flash(svc.uiName + " " + message + ".", "success", 5000);
    }

    function _itemList() {
        return svc.listScope[svc.listProp];
    }

    function _unusedEventTypes() {
        return svc.listScope.eventTypes.filter(function(et) {
            return _itemList().every(function(alert) {
                return alert.event_type !== et.value;
            });
        });
    };

    svc.createEmpty = function createEmpty() {
        var event_type = _unusedEventTypes()[0];
        return {
            id: null,
            label: event_type.label,
            event_type: event_type.value,
            template: ''
        };
    };

    svc.create = function create(alert) {
        var data = {
            event_type: alert.event_type,
            template: alert.template
        };
        return svc.client.save(data);
    };

    svc.populateListScope = function populateListScope(listScope, response) {
        listScope[svc.listProp] = response[svc.listProp];
        svc.listScope = listScope;
    };

    svc.fillModalScope = function fillModalScope(scope, object) {
        scope.alert = object;
        scope.eventTypes = svc.listScope.eventTypes;
        scope.unusedEventTypes = _unusedEventTypes();
    };

    svc.objectCreated = function objectCreated(alert) {
        _itemList().push(alert);
        _showMessage("added");
    };

    svc.objectUpdated = function objectUpdated(alert) {
        var items = _itemList();
        for (var i = 0; i < items.length; i += 1) {
            var obj = items[i];
            if (obj.id === alert.id) {
                items[i] = alert;
                break;
            }
        }
        _showMessage("updated");
    };

    svc.objectDeleted = function objectDeleted(alert) {
        var items = _itemList();
        items.splice(items.indexOf(alert), 1);
        _showMessage("deleted");
    };

    svc.asyncDelete = function deleteObj(alert) {
        var d = $q.defer();
        svc.remove(alert.id).then(function(result) {
            svc.objectDeleted(alert);
            d.resolve();
        });
        return d.promise;
    };

    return svc;
}
