
$(function() {
    var $collected = $('#id_collected');

    if($collected.length > 0) {
        var $collectedLabel = $('label[for="id_collected"]');

        // add link after today field
        $collectedLabel.append('<a id="collected-today-link" href="#">Today</a>');

        // give it an on click listener to set the field to the current date/time
        $('#collected-today-link').on('click', function (e) {
            e.preventDefault();
            $collected.val(getCurrentDateTimeString());
        })
    }

});
