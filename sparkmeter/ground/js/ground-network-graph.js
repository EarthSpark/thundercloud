// -*- coding: utf-8 -*-
// Copyright © 2013-2016 SparkMeter, Inc.
// All Rights Reserved.
//

/* globals d3 */

function load_json(rssi, topn) {
    // FIXME: maybe I can just clear the links instead of rebuilding the entire graph from scratch
    $('svg').remove();

    var width = 6000;
    var height = 4000;
    d3.scale.category20();
    var width2 = width / 2;
    var height2 = height / 2;
    var svg = d3.select("body")
        .append("svg")
        .attr("width", width)
        .attr("height", height);

    var force = d3.layout.force()
        .gravity(0.05)
        .distance(function(d) {
            return (83 + d.ninv_rssi) * 5;
        })
        .charge(-150)
        .size([width, height]);

    d3.json("force.json?rssi=" + rssi + "&topn=" + topn, function(json) {
        force
            .nodes(json.nodes)
            .links(json.links)
            .start();

        var link = svg.selectAll(".link")
            .data(json.links)
            .enter().append("line")
            .attr("class", "link")
            .attr("ninv_rssi", function(d) {
                return d.ninv_rssi;
            });

        var color = d3.scale.category20();

        var node = svg.selectAll(".node")
            .data(json.nodes)
            .enter().append("g")
            .attr("class", "node")
            .call(force.drag);

        node.append("circle")
            .attr("r", function(d) {
                switch (d.node_type) {
                    case 'forwarder':
                        return 10;
                    case 'gateway':
                        return 12;
                    default:
                        return 8;
                }
            })
            .style("fill", function(d) {
                return color(d.id === 0 ? 1 : 2);
            });

        node.append("text")
            .attr("dx", 12)
            .attr("dy", ".35em")
            .text(function(d) {
                return d.name;
            });

        force.on("tick", function() {
            link.attr("x1", function(d) {
                return isNaN(d.source.x) ? width2 : d.source.x;
            })
                .attr("y1", function(d) {
                    return isNaN(d.source.y) ? height2 : d.source.y;
                })
                .attr("x2", function(d) {
                    return isNaN(d.target.x) ? width2 : d.target.x;
                })
                .attr("y2", function(d) {
                    return isNaN(d.target.y) ? height2 : d.target.y;
                });

            node.attr("transform", function(d) {
                var x = isNaN(d.x) ? width2 : d.x;
                var y = isNaN(d.y) ? height2 : d.y;
                return "translate(" + x + "," + y + ")";
            });
        });
    });
}

// update the elements
function update(rssi, topn) {
    // adjust the text on the range slider
    d3.select("#rssi-value").text(rssi);
    d3.select("#rssi").property("value", rssi);
    d3.select("#topn-value").text(topn);
    d3.select("#topn").property("value", topn);
    load_json(rssi, topn);
}

function setupNetworkGraph() {
    // when the input range changes update the circle
    d3.select("#rssi").on("input", function() {
        update(d3.select("#rssi").property("value"),
            d3.select("#topn").property("value"));
    });

    d3.select("#topn").on("input", function() {
        update(d3.select("#rssi").property("value"),
            d3.select("#topn").property("value"));
    });

    // Initial starting radius of the circle
    update(90, 0);
}

window.setupNetworkGraph = setupNetworkGraph;
