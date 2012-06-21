$j(document).ready(function(){
    $j('.color').each(function(i){
	$j(this).spectrum({
	    showInput: true,
	    showPalette: true,
	    showInitial: true,
	    showButtons: false
	});
    });
})

