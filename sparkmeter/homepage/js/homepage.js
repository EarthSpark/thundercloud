// -*- coding: utf-8 -*-
// Copyright © 2013-2016 SparkMeter, Inc.
// All Rights Reserved.
//

var base = require('base.js');

base.registerPageLoader('homepage-view', function() {
    var CustomerMeterList = require('meter/js/meter-list-customer.js');
    new CustomerMeterList.CustomerMeterList();

    if ($('meta[itemprop=config-vendor]').attr('content') !== 'true') {
        var TotalizerMeterList = require('meter/js/meter-list-totalizer.js');
        new TotalizerMeterList.TotalizerMeterList();
    }

    var SalesAccountList = require('salesaccount/js/sales-account-list.js');
    new SalesAccountList.SalesAccountList({
        page: SalesAccountList.PAGE_MY
    });
});
