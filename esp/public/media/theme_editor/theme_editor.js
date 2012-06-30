function showColor() {
    $j('.color').each(function(i){
	$j(this).spectrum({
	    showInput: true,
	    showPalette: true,
	    showInitial: true,
	    showButtons: false,
	    preferredFormat: "name",
	    palette: [palette_list],
	    showPaletteOnly: true
	});
    })
	}

function showPalette() {
    $j('.palette').each(function(i){
	$j(this).spectrum({
	    showInput: true,
	    showPalette: true,
	    showInitial: true,
	    showButtons: false,
	    preferredFormat: "name",
	    palette: [palette_list]
	});
    })
	}
		     

$j(document).ready(function(){
    showColor();
    showPalette();
    $j('#addToPalette').click(function(){
	var newColor = $j('<input>');
	newColor.addClass('palette');
	newColor.attr({
	    name: 'palette',
	    type: 'text',
	    value: 'black'
	});
	$j('#palette_div').append(newColor);
	showPalette()
    });

    $j('#removeFromPalette').click(function(){
	$j('#palette_div div.sp-replacer.sp-light:last').remove();
	$j('#palette_div input:last').remove()
    });    
    $('[rel=popover]').each(function(){
	$(this).popover({placement:'left', animation:false}); //interesting bug: $ calls jquery 1.7.1 but $j calls the older version
    });
});





