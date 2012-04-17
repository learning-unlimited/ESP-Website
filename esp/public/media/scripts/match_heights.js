
//  Adapted from http://www.devarticles.com/c/a/Web-Design-Standards/Matching-div-heights-with-CSS-and-JavaScript/3/

match_heights = function(div_ids){
     var divs,contDivs,maxHeight,divHeight,d;
     // get <div> elements
     divs=[];
     var got_div;
     for (var i in div_ids)
     {
	 got_div = document.getElementById(div_ids[i]);
	 if (got_div) {
	     divs.push(got_div);
	 }
     }
     contDivs=[];
     // initialize maximum height value
     maxHeight=0;
     // iterate over <div> elements
     for(var i=0;i<divs.length;i++){
        d=divs[i];
        contDivs[contDivs.length]=d;
        // determine height for <div> element
	divHeight = $j(d).height();
        // calculate maximum height
        maxHeight=Math.max(maxHeight,divHeight);
     }
     // assign maximum height value to all of container <div> elements
     for(var i=0;i<contDivs.length;i++){
        contDivs[i].style.height= maxHeight + 'px';
     }
}
