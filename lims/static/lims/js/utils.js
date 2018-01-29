
function getCurrentDateTimeString() {
    var date = new Date();
    var tzOffsetMinutes = date.getTimezoneOffset();
    var datePretendingToBeUTC = new Date(date.getTime() - tzOffsetMinutes * 60 * 1000);
    return datePretendingToBeUTC
        .toISOString()
        .replace(/T/, ' ')
        .replace(/:[0-9]{2}\.[0-9]*Z$/, '');
}
