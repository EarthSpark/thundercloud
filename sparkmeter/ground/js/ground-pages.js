// -*- coding: utf-8 -*-
// Copyright © 2013-2016 SparkMeter, Inc.
// All Rights Reserved.
//

var base = require('base.js');

base.registerPageLoader('ground-graph', function() {
    var networkGraph = require('ground/js/ground-network-graph.js');
    networkGraph.setupNetworkGraph();
});

base.registerPageLoader('ground-status', function() {
    var boot_time = $("#ground-status").attr("data-boot-time");
    var date = new Date(boot_time * 1000);
    $(".box-content.boottime").text(date);
});

base.registerPageLoader('ground-override', function() {
    var groundOverride = require('ground/js/ground-override.js');
    groundOverride.groundOverride();
});
