// -*- coding: utf-8 -*-
// Copyright © 2013-2016 SparkMeter, Inc.
// All Rights Reserved.
//

var base = require('base.js');
// FIXME: Figure out how to do this in a page-loader, can't be done in a normal
// page loader as it is too late for Angular to render the page properly.
require('core.app.js');
require('crud-client-service.js');
require('datatables.js');
require('modal-item-service.js');
require('modal-item-service.controller.js');
require('config/js/sms.app.js');
require('config/js/sms.directives.js');
require('config/js/smsalert.controller.js');
require('config/js/smsalert.js');
require('config/js/smscommand.controller.js');
require('config/js/smscommand.js');
require('config/js/smsconfigmessages.controller.js');
require('config/js/smsconfigmessages.js');
require('config/js/smseventtypes.js');
require('config/js/smsexamplerenderer.js');
require('config/js/smstemplate.js');

base.registerPageLoader('billing-settings', function() {
    var SettingsPage = require('config/js/settingspage.js');
    new SettingsPage.SettingsPage(['allow-negative-balance', 'debt-payback-percent']);
});

base.registerPageLoader('meter-settings', function() {
    var SettingsPage = require('config/js/settingspage.js');
    new SettingsPage.SettingsPage(['nominal-voltage']);

    var MeterList = require('config/js/meter-list.js');
    new MeterList.MeterList();
});
