function utcnow() {
    return parseInt(new Date().getTime() / 1000, 10);
}
exports.utcnow = utcnow;

function astimestamp(date) {
    return parseInt(new Date(date + "+00:00").getTime() / 1000, 10);
}
exports.astimestamp = astimestamp;

var _intervals = [
    {labels: ['month', 'months'], seconds: 2592000},
    {labels: ['day', 'days'], seconds: 86400},
    {labels: ['hour', 'hours'], seconds: 3600},
    {labels: ['minute', 'minutes'], seconds: 60},
    {labels: ['second', 'seconds'], seconds: 0}
];

function formatDelta(t) {
    if (!t) return "";
    t = Math.abs(t);
    var seconds = Math.floor(t);
    var interval = _intervals.find(function(i) {
        return i.seconds < seconds;
    });
    var count = Math.floor(seconds / interval.seconds);
    return count + " " + interval.labels[(count !== 1) & 1];
}
exports.formatDelta = formatDelta;

/* Format a time according to ISO8601 date, eg: 2017-11-07 16:20:34
*/
function formatDate(date) {
    var iso = date.toISOString().match(/(\d{4}\-\d{2}\-\d{2})T(\d{2}:\d{2}:\d{2})/);
    return iso[1] + ' ' + iso[2];
}
exports.formatDate = formatDate;
