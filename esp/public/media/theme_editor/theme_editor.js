function showColor() {
    $j('.color').each(function(i){
        var default_color = $j(this).data("default");
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
        var resetButton = $j('<button class="reset-color" type="button" style="margin-left: 1.5px;">Reset Color</button>').on('click', function() {
            $j(this).siblings("input").spectrum("set", default_color); // Reset color to default
        });
        // Create the "Remove" button
        var removeButton = $j('<button class="remove-color" type="button" style="margin-left: 5px;">Remove Variable</button>').on('click', function() {
            var input = $j(this).siblings("input");
            input.spectrum("destroy");
            $j(this).parents(".control-group").remove();
            $j("option[value=" + input.attr("name") + "]").show();
        });
        if ($j(this).siblings(".reset-color").length == 0) {
            $j(this).parent(".controls").append(resetButton);
        }
        var reg = new RegExp("optional", "i");
        if (reg.test($j(this).parents("[id^=adv_category]").children("h3").text()) && $j(this).siblings(".remove-color").length == 0) {
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
    $j("#palette_custom_div .sp-replacer").on('click', function(e) {
        $active = $j(e.target).closest(".sp-replacer").prev();
    });
    $j(".sp-container button.sp-cancel").on('click', function(e) {
        $active.spectrum("destroy");
        $active.remove();
    });
}

$j(document).ready(function(){
    
    showColor();
    showBasePalette();
    showCustomPalette();
    $j(".length, .text").each(function(){
        var el = $j(this)
        var default_val = el.data("default");
        var resetButton = $j('<button class="reset-length" type="button" style="margin-left: 1.5px;">Reset</button>').on('click', function() {
            el.val(default_val); // Reset to default value
        });
        el.parent(".controls").append(resetButton);
    });
    $j('#addToPalette').on('click', function(){
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
    
    //  Make optional variable dropdown blank
    $j('select.select_opt_var').val('');
    
    //  Allow form elements to be created for optional variables
    $j('button.add_opt_var_button').on('click', function (event) {
        event.preventDefault();
        
        // Determine which optional variable we are trying to add.
        var button_id = event.target.id;
        var button_id_prefix = 'add_opt_var_';
        var select_id = 'new_opt_var_' + button_id.substr(button_id_prefix.length);
        var select_el = $j('#' + select_id);
        var select_val = select_el.val();
        var option_el = select_el.find(":selected");
        var default_color = option_el.data('default');
        option_el.hide();
        select_el.val("");
        
        // Don't want duplicate variables
        if ($j("#id_" + select_val).length == 0) {
            // Create a new color input field
            var colorInput = $j('<input>')
                .attr({
                    id: 'id_' + select_val,
                    class: 'color',
                    type: 'text',
                    value: default_color,
                    name: select_val,
                    style: 'display: none;'
                });

            // Create the "Reset Color" button
            var resetButton = $j('<button class="reset-color" type="button" style="margin-left: 5px;">Reset Color</button>').on('click', function() {
                $j(this).siblings("input").spectrum("set", default_color); // Reset color to default
            });

            // Create the "Remove" button
            var removeButton = $j('<button class="remove-color" type="button" style="margin-left: 5px;">Remove Variable</button>').on('click', function() {
                $j(this).siblings("input").spectrum("destroy");
                $j(this).parents(".control-group").remove();
                option_el.show();
            });

            // Create a control group and append the color input and reset button
            var controlsDiv = $j('<div class="controls">')
                .append(colorInput)
                .append(resetButton)
                .append(removeButton);
            var controlGroup = $j('<div class="control-group">')
                .append($j('<label class="control-label" for="' + select_val + '">').html(select_val))
                .append(controlsDiv)

            // Append the control group to the parent element
            $j(event.target).parent().parent().parent().append(controlGroup);

            showColor();
        }
    });
});
