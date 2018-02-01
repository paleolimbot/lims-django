
$(function() {

    // make the print button print things
    $('#print-barcodes-submit').on('click', function(e) {
        e.preventDefault();
        window.print();
    });

    // respond to change of label size
    function setLabelSize(value) {
        var allClasses = ['qrcode-full-label-small', 'qrcode-full-label-medium', 'qrcode-full-label-large'];
        var newClass = 'qrcode-full-label-' + value;
        if(allClasses.indexOf(newClass) === -1) {
            console.log('unknown new class: ' + newClass);
        }

        $('.qrcode-full-label').removeClass(allClasses).addClass(newClass);
    }

    // set onclick listener for radios
    $('input[type="radio"][name="label_size"]').on('change', function() {
        setLabelSize(this.value);
    });

    // sync radio value with label size
    var currentSize = $('input[type="radio"][name="label_size"]:checked').val()
    if(currentSize) {
        setLabelSize(currentSize)
    }
});
