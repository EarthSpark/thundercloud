// -*- coding: utf-8 -*-
// Copyright © 2013-2017 SparkMeter, Inc.
// All Rights Reserved.
//

function formatSalesAccountLink(account_id, account_name) {
    return '<a href="/sales-account/' + account_id + '/">' +
        account_name + '</i></a>';
}

exports.formatSalesAccountLink = formatSalesAccountLink;
