// -*- coding: utf-8 -*-
// Copyright © 2013-2016 SparkMeter, Inc.
// All Rights Reserved.
//

var path = require('path');

var config = {
    entry: {
        application: [
            './assets/javascripts/startup.js'
        ]
    },
    module: {},
    output: {
        filename: '[name].js'
    },
    resolve: {
        root: [
            path.resolve('assets/javascripts'),
            path.resolve('sparkmeter')
        ]
    },
    resolveLoader: {
        root: [
            path.resolve('scripts/config/node_modules')
        ]
    },
    watchOptions: {
        poll: 1000
    }
};
module.exports = config;
