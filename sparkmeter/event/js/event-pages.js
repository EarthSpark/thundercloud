// -*- coding: utf-8 -*-
// Copyright © 2013-2018 SparkMeter, Inc.
// All Rights Reserved.
//

$(function() {
    if ($('table#message-list').length) {
        var MessageList = require('event/js/smsmessagelist.js');
        new MessageList.MessageList();
    }
});
