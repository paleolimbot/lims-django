
function addForms(n) {
    // make sure n is an integer. if it isn't, don't do anything
    n = parseInt(n);
    if(isNaN(n)) {
        return;
    }

    var $container = $('#add-formset-list');
    var $header = $('#add-formset-header').parent();
    var $formLi = $container.find('.add-formset-item').not($header);

    // setup the template (no errors, no values)
    var $template = $formLi.first().clone();
    $template.find('.errorlist').remove();
    $template.find('input[type="text"]').val('');

    var n_forms = $formLi.length;

    for(var i=0; i<n; i++) {
        var nth_form = n_forms + i + 1;
        var $newLi = $template.clone();

        // update id and name on input elements
        $newLi.find('input').each(function() {
            var $this = $(this);
            var current_id = $this.attr('id');
            var current_name = $this.attr('name');
            $this.attr('id', current_id.replace(/[0-9]+/, nth_form));
            $this.attr('name', current_name.replace(/[0-9]+/, nth_form));
        });

        // update for element on label elements
        $newLi.find('label').each(function() {
            var $this = $(this);
            $this.attr('for', $this.attr('for').replace(/[0-9]+/, nth_form))
        });

        $container.append($newLi);
    }
}

function fillDown(linkId) {
    var $link = $(linkId);
    var fieldName = $link.attr('id').replace(/-(fill|clear|today)$/, '');
    var action = $link.attr('id').replace(/^[a-z_]+-/, '');

    if(action === 'fill') {
        // get the value from the fist field
        var value = $('#id_form-0-' + fieldName).val();

        // if there is no value, do nothing
        if (value.length === 0) {
            return;
        }

        // set all non-blank cells to value
        $('#add-formset-list').find('input[type="text"]').each(function() {
            var $this = $(this);
            if($this.attr('name').endsWith(fieldName) && $this.val() === '') {
                $this.val(value);
            }
        })
    } else if (action === 'clear') {
        // set all cells to ''
        $('#add-formset-list').find('input[type="text"]').each(function() {
            var $this = $(this);
            if($this.attr('name').endsWith(fieldName)) {
                $this.val('');
            }
        })
    } else if (action === 'today' && fieldName === 'collected') {
        var dateString = new Date().toISOString().replace(/T/, ' ').replace(/:[0-9]{2}\.[0-9]*Z$/, '');
        $('#id_form-0-' + fieldName).val(dateString);
    } else {
        console.log('Unknown action: "' + action + '"');
    }
}

$(function() {
    $('#add-formset-more-go').on('click', function(e) {
        e.preventDefault();
        addForms($('#add-formset-more-number').val());
    });

    $('#add-formset-header').on('click', 'a', function(e) {
        e.preventDefault();
        fillDown(this);
    })
});
