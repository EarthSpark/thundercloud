// -*- coding: utf-8 -*-
// Copyright © 2013-2016 SparkMeter, Inc.
// All Rights Reserved.
//
// Message handling

/* global angular */

var base = require('base.js');

angular
    .module('sparkmeter.event.sms')
    .factory('SMSConfigMessagesService', SMSConfigMessagesService);

SMSConfigMessagesService.$inject = ['CrudClientService'];

function SMSConfigMessagesService(CrudClientService) {
    var svc = this;
    _activate();

    function _activate() {
        svc.uiName = "SMS Message";
        svc.createProp = "message_id";
        svc.readProp = "message";
        svc.listProp = "messages";
        svc.templateUrl = 'sms-config-message-modal.html';
        svc.client = new CrudClientService("/alert/config/smsmessages/:id");
        svc.read = svc.client.read.bind(svc.client);
        svc.update = svc.client.update.bind(svc.client);
        svc.list = svc.client.list.bind(svc.client);
    }

    function _showMessage(message) {
        base.flash(svc.uiName + " " + message + ".", "success", 5000);
    }

    function _itemList() {
        return svc.listScope[svc.listProp];
    }

    svc.populateListScope = function populateListScope(listScope, response) {
        listScope[svc.listProp] = response[svc.listProp];
        svc.listScope = listScope;
    };

    svc.fillModalScope = function fillModalScope(scope, object) {
        scope.message = object;
        scope.messageTypes = svc.listScope.messageTypes;
        scope.messageLabels = svc.listScope.messageLabels;
    };

    svc.objectUpdated = function objectUpdated(message) {
        var items = _itemList();
        for (var i = 0; i < items.length; i += 1) {
            var obj = items[i];
            if (obj.id === message.id) {
                items[i] = message;
                break;
            }
        }
        _showMessage("updated");
    };

    return svc;
}
