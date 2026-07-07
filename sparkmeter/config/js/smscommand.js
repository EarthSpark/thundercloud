// -*- coding: utf-8 -*-
// Copyright © 2013-2016 SparkMeter, Inc.
// All Rights Reserved.
//
// Command handling

/* global angular */

var base = require('base.js');

angular
    .module('sparkmeter.event.sms')
    .factory('SMSCommandsService', SMSCommandsService);

SMSCommandsService.$inject = ['CrudClientService', '$q'];

function SMSCommandsService(CrudClientService, $q) {
    var svc = this;
    _activate();

    function _activate() {
        svc.uiName = "Two-way SMS";
        svc.createProp = "command_id";
        svc.readProp = "command";
        svc.listProp = "commands";
        svc.templateUrl = 'sms-config-command-modal.html';

        svc.client = new CrudClientService("/alert/config/smscommands/:id");
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

    svc.createEmpty = function createEmpty() {
        return {
            id: null,
            code: '',
            template: ''
        };
    };

    svc.create = function create(command) {
        var data = {
            code: command.code,
            template: command.template
        };
        return svc.client.save(data);
    };

    svc.populateListScope = function populateListScope(listScope, response) {
        listScope[svc.listProp] = response[svc.listProp];
        svc.listScope = listScope;
    };

    svc.fillModalScope = function fillModalScope(scope, object) {
        scope.$watch('command.code', function(code) {
            var isDuplicate = _itemList().some(function(command) {
                if (command.id === object.id) {
                    return false;
                } else {
                    return command.code === code;
                }
            });
            scope.form.code.$setValidity('duplicate', isDuplicate !== true);
        });
        scope[svc.listProp] = svc.listScope[svc.listProp];
        scope.command = object;
        scope.eventTypes = svc.listScope.eventTypes;
    };

    svc.objectCreated = function objectCreated(command) {
        _itemList().push(command);
        _showMessage("added");
    };

    svc.objectUpdated = function objectUpdated(command) {
        var items = _itemList();
        for (var i = 0; i < items.length; i += 1) {
            var obj = items[i];
            if (obj.id === command.id) {
                items[i] = command;
                break;
            }
        }
        _showMessage("updated");
    };

    svc.objectDeleted = function objectDeleted(command) {
        var items = _itemList();
        items.splice(items.indexOf(command), 1);
        _showMessage("deleted");
    };

    svc.asyncDelete = function deleteObj(command) {
        var d = $q.defer();
        svc.remove(command.id).then(function(result) {
            svc.objectDeleted(command);
            d.resolve();
        });
        return d.promise;
    };

    return svc;
}
