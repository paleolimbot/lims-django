
function addForms(n) {
    // make sure n is an integer. if it isn't, don't do anything
    n = parseInt(n);
    if(isNaN(n)) {
        return;
    }

    var $container = $('#add-formset-list');
    var $header = $('#add-formset-tools').parent();
    var $formLi = $container.find('.add-formset-item').not($header);

    // setup the template (no errors, no values)
    var $template = $formLi.first().clone();
    $template.find('.errorlist').remove();
    $template.find('input[type="text"]').val('');

    var n_forms = $formLi.length;

    for(var i=0; i<n; i++) {
        var nth_form = n_forms + i;
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
        var dateString = getCurrentDateTimeString();
        $('#id_form-0-' + fieldName).val(dateString);
    } else {
        console.log('Unknown action: "' + action + '"');
    }
}

function pasteTable(input, e) {
    var $active = $(input);
    var activeId = $active.attr('id');
    var text = e.originalEvent.clipboardData.getData('text');
    var textLines = text.split('\n');

    // get the row and column info, so newlines and tabs can be processed accordingly
    var fields = ['collected', 'name', 'description', 'location_slug', 'tag_json'];
    var idInfo = activeId.match(/id_form-([0-9]+)-(.*)$/);
    var row = parseInt(idInfo[1]);
    var col = fields.indexOf(idInfo[2]);

    // function to get ID for rando row/col combo
    function getFieldId(newrow, newcol) {
        if(newcol >= fields.length) {
            return null;
        }

        return 'id_form-' + newrow + '-' + fields[newcol];
    }

    // loop through lines of pasted text (will quietly ignore too many rows/cols of pasted text
    for(var i=0; i < textLines.length; i++) {
        var textCells = textLines[i].split('\t');
        // loop through tab-separated cells of pasted text
        for(var j=0; j < textCells.length; j++) {
            var fieldId = getFieldId(row + i, col + j);
            if(fieldId !== null) {
                $('#' + fieldId).val(textCells[j].trim());
            }
        }
    }
}

$(function() {
    $('#add-formset-more-go').on('click', function(e) {
        e.preventDefault();
        addForms($('#add-formset-more-number').val());
    });

    $('#add-formset-tools').on('click', 'a', function(e) {
        e.preventDefault();
        fillDown(this);
    });

    $('#add-formset-list').on('paste', 'input', function(e) {
        e.preventDefault();
        pasteTable($(this), e);
    })
});
