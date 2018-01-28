
function registerTableForm(formId) {
    // find sample form
    var $tableForm = $(formId);

    // if there is one...
    if($tableForm.length !== 0) {

        // checkbox elements
        var $checks = $tableForm.find('input[type="checkbox"]').not('input[name="object-all-selected"]');
        var $checkAll = $tableForm.find('input[name="object-all-selected"]');
        var $lastSelected = $();

        // action selection should result in submitting the form
        $tableForm.find('select[name="action"]').on('change', function() {
            var $selected = $checks.filter(':checked');
            if($(this).val() !== '' && $selected.length > 0) {
                $tableForm.submit();
            }
        });

        // checkbox logic click listener
        $tableForm.on('click', 'input[type="checkbox"]', function() {
            var $this = $(this);
            var check_state = $this.prop('checked');
            if($this.is($checkAll)) {
                // check all logic
                $checks.prop('checked', check_state);
                // forget last clicked item
                $lastSelected = $();
            } else {
                // shift-select logic
                if(shiftKeyDown && $lastSelected) {

                    // $this and $lastSelected state must match
                    if($this.prop('checked') === $lastSelected.prop('checked')) {

                        // get the index of this element, last checked element in $checks
                        var thisIndex = $checks.index($this);
                        var lastIndex = $checks.index($lastSelected);

                        // toggle everything inbetween the two indicies (not including lastSelected)
                        $checks.slice(Math.min(lastIndex, thisIndex), Math.max(lastIndex, thisIndex))
                            .not($lastSelected)
                            .prop('checked', $this.prop('checked'));
                    }

                }

                // sync the check state with the select all checker
                var $notSelected = $checks.not(':checked');
                $checkAll.prop('checked', $notSelected.length === 0);

                // set lastSelected to this element
                $lastSelected = $this;
            }
        });

        return true;
    } else {
        return false;
    }
}

$(function() {
    // find sample, location lists and register the click listeners
    var hasSampleTable = registerTableForm('#sample-viewlist-form');
    var hasLocationTable = registerTableForm('#location-viewlist-form');
    if(hasSampleTable || hasLocationTable) {

        // register the onKeyDown listener for the shift key
        window.shiftKeyDown = false;
        $(document).on('keyup keydown', function(e){
            console.log('shift key pressed');
            window.shiftKeyDown = e.shiftKey;
        } );

    }
});
