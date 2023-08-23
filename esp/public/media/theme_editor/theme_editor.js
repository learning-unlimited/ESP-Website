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
            cancelText: "Remove",
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
    
    $j('[rel=popover]').each(function(){
        $j(this).popover({placement:'left', animation:false});
    });
    
    $j('div.opt_var_div:has(select.select_opt_var:has(option))').removeClass('hidden');
    
    $j('button.add_opt_var_button').click(function (event) {
        event.preventDefault();
        
        // Determine which optional variable we are trying to add.
        var button_id = event.target.id;
        var button_id_prefix = 'add_opt_var_';
        var select_id = 'new_opt_var_' + button_id.substr(button_id_prefix.length);
        var select_val = $j('#' + select_id).val();
        
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
        var resetButton = $j('<button class="reset-color">Reset Color</button>').click(function() {
            colorInput.spectrum("set", "#000000"); // Reset color to default
        });

        // Create a control group and append the color input and reset button
        var controlGroup = $j('<div class="control-group">')
            .append($j('<label class="control-label" for="' + select_val + '">').html(select_val))
            .append(colorInput)
            .append(resetButton);

        // Append the control group to the parent element
        $j(event.target).parent().parent().parent().append(controlGroup);

        showColor();
    });
});
