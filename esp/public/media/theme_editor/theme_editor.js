function showColor() {
    $j('.color').each(function(i){
        $j(this).spectrum({
            type: "color",
            showInput: true,
            showInitial: true,
            showButtons: false,
            preferredFormat: "hex",
            palette: [palette_list],
            showPaletteOnly: true
        });
        // Create the "Reset Color" button
        var resetButton = $j('<button class="reset-color" type="button" style="margin-left: 1.5px;">Reset Color</button>').click(function() {
            $j(this).siblings("input").spectrum("set", "#000000"); // Reset color to default
        });
        // Create the "Remove" button
        var removeButton = $j('<button class="remove-color" type="button" style="margin-left: 5px;">Remove Variable</button>').click(function() {
            $j(this).siblings("input").spectrum("destroy");
            $j(this).parent(".control-group").remove();
        });
        if ($j(this).siblings(".reset-color").length == 0) {
            $j(this).parent(".controls").append(resetButton);
        }
        if ($j(this).filter("[id*=accent]").length == 1 && $j(this).siblings(".remove-color").length == 0) {
            $j(this).parent(".controls").append(removeButton);
        }
    });
}

function showBasePalette() {
    $j('#palette_base_div .palette').each(function(i){
        $j(this).spectrum({
            type: "color",
            showInput: true,
            allowEmpty: false,
            showPalette: false,
            showInitial: true,
            showButtons: true,
            preferredFormat: "hex",
            disabled: true
        });
    });
}

function showCustomPalette() {
    $j('#palette_custom_div .palette').each(function(i){
        $j(this).spectrum({
            type: "color",
            showInput: true,
            allowEmpty: false,
            showPalette: false,
            showInitial: true,
            showButtons: true,
            preferredFormat: "hex",
            cancelText: "Remove"
        });
    });
    var $active;
    $j("#palette_custom_div .sp-replacer").click(function(e) {
        $active = $j(e.target).closest(".sp-replacer").prev();
    });
    $j(".sp-container button.sp-cancel").click(function(e) {
        $active.spectrum("destroy");
        $active.remove();
    });
}

$j(document).ready(function(){
    showColor();
    showBasePalette();
    showCustomPalette();
    $j('#addToPalette').click(function(){
        var newColor = $j('<input>');
        newColor.addClass('palette');
        newColor.attr({
            name: 'palette',
            type: 'text',
            value: 'black'
        });
        $j('#palette_custom_div').append(newColor);
        $j('#palette_custom_div').append(" ");
        showCustomPalette();
    });

    $j('[rel=popover]').each(function(){
        $j(this).popover({placement:'left', animation:false});
    });
    
    //  Show optional variable selector if there are optional variables available
    $j('div.opt_var_div:has(select.select_opt_var:has(option))').removeClass('hidden');
    
    //  Allow form elements to be created for optional variables
    $j('button.add_opt_var_button').click(function (event) {
        event.preventDefault();
        
        // Determine which optional variable we are trying to add.
        var button_id = event.target.id;
        var button_id_prefix = 'add_opt_var_';
        var select_id = 'new_opt_var_' + button_id.substr(button_id_prefix.length);
        var select_val = $j('#' + select_id).val();
        
        // Don't want duplicate variables
        if ($j("#id_" + select_val).length == 0) {
            // Create a new color input field
            var colorInput = $j('<input>')
                .attr({
                    id: 'id_' + select_val,
                    class: 'color',
                    type: 'text',
                    value: '#000000',
                    name: select_val,
                    style: 'display: none;'
                });

            // Create the "Reset Color" button
            var resetButton = $j('<button class="reset-color" type="button" style="margin-left: 5px;">Reset Color</button>').click(function() {
                $j(this).siblings("input").spectrum("set", "#000000"); // Reset color to default
            });

            // Create the "Remove" button
            var removeButton = $j('<button class="remove-color" type="button" style="margin-left: 5px;">Remove Variable</button>').click(function() {
                $j(this).siblings("input").spectrum("destroy");
                $j(this).parent(".control-group").remove();
            });

            // Create a control group and append the color input and reset button
            var controlGroup = $j('<div class="control-group">')
                .append($j('<label class="control-label" for="' + select_val + '">').html(select_val))
                .append(colorInput)
                .append(resetButton)
                .append(removeButton);

            // Append the control group to the parent element
            $j(event.target).parent().parent().parent().append(controlGroup);

            showColor();
        }
    });
});
