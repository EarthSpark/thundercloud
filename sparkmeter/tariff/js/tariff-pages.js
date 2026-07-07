// -*- coding: utf-8 -*-
// Copyright © 2013-2016 SparkMeter, Inc.
// All Rights Reserved.
//

var base = require('base.js');

base.registerPageLoader('tariff-form', function() {
    var TariffForm = require('tariff/js/tariff-form.js');
    new TariffForm.TariffForm();
});

base.registerPageLoader('tariff-list', function() {
    var TariffList = require('tariff/js/tariff-list.js');
    new TariffList.TariffList();
});

base.registerPageLoader('tariff-view', function() {
    var TariffView = require('tariff/js/tariff-view.js');
    new TariffView.TariffView();
});
