/*
A jQuery plugin to convert a well formatted table into a table with fixed
rows and columns.
Copyright (C) (2011-2012) Selvakumar Arumugam
This program is free software: you  can redistribute it and/or modify it
under the  terms of the GNU  General Public License as  published by the
Free Software Foundation,  either version 3 of the License,  or (at your
option) any later version.
This  program  is distributed  in  the  hope  that  it will  be  useful,
but  WITHOUT  ANY  WARRANTY;  without   even  the  implied  warranty  of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General
Public License for more details.
You should have received a copy  of the GNU General Public License along
with this program. If not, see <http://www.gnu.org/licenses/>.
*/
(function ($) {
    
    $.fn.fxdHdrCol = function (o) {
        var cfg = {
            height: 0,
            width: 0,       
            fixedCols: 0,
            colModal: [],           
            tableTmpl: function () {
                return '<table />';                         
            },
            sort: false
        };
        $.extend(cfg, o);
        
        return this.each (function () {
            var lc = {
                    ft_container: null,
                    ft_rel_container: null,
                    ft_wrapper: null,
                    ft_rc: null,
                    ft_r: null,
                    ft_c: null,
                    tableWidth: 0
            };
            
            var $this = $(this);
            $this.addClass('ui-widget-header');
            $this.find('tbody tr').addClass('ui-widget-content');
                                
            $this.wrap('<div class="ft_container" />');
            lc.ft_container = $this.parent().css({width: cfg.width, height: cfg.height});       
            
            var $ths = $('thead tr', $this).first().find('th');
            
            if (cfg.sort && sorttable && cfg.fixedCols == 0) {              
                $ths.addClass('fx_sort_bg');                
            }

            var $thFirst = $ths.first();
            var thSpace = parseInt($thFirst.css('paddingLeft'), 10) + parseInt($thFirst.css('paddingRight'), 10);

            /* set width and textAlign from colModal */
            var ct = 0;
            $ths.each(function (i, el) {
                var calcWidth = 0;
                for (var j = 0; j < el.colSpan; j++) {
                    calcWidth += cfg.colModal[ct].width;
                    ct++;
                }
                $(el).css({width: calcWidth, textAlign: cfg.colModal[ct-1].align});
                
                lc.tableWidth += calcWidth + thSpace + ((i == 0)?2:1);
            });
                                
            $('tbody', $this).find('tr').each(function (i, el) {
                $('td', el).each(function (i, tdel) {
                    tdel.style.textAlign = cfg.colModal[i].align;
                });
            });
            
            $this.width(lc.tableWidth);

            //add relative container
            $this.wrap('<div class="ft_rel_container" />');
            lc.ft_rel_container = $this.parent();
                        
            //add wrapper to base table which will have the scrollbars
            $this.wrap('<div class="ft_scroller" />');
            lc.ft_wrapper = $this.parent().css('width', cfg.width - 5);
            
            var theadTr = $('thead', $this);
            //clone the thead->tr 
            var theadTrClone = theadTr.clone();
            
            //construct fixed row (full row)
            lc.ft_rel_container
                .prepend($(cfg.tableTmpl(), {'class': 'ft_r ui-widget-header'})
                .append(theadTrClone));

            //an instance of fixed row
            lc.ft_r = $('.ft_r', lc.ft_rel_container);
            lc.ft_r.wrap($('<div />', {'class': 'ft_rwrapper'}));
            
            lc.ft_r.width(lc.tableWidth);
            
            if (cfg.fixedCols > 0) {
                //clone the thead again to construct the 
                theadTrClone = theadTr.clone();
                
                //calculate the actual column's count (support for colspan)                 
                var r1c1ColSpan = 0;        
                for (var i = 0; i < cfg.fixedCols; i++ ) {
                    r1c1ColSpan += this.rows[0].cells[i].colSpan;           
                }                   
                
                //prepare rows/cols for fixed row col section
                var tdct = 0;
                $('tr', theadTrClone).first().find('th').filter( function () {
                    tdct += this.colSpan;
                    return tdct > r1c1ColSpan;
                }).remove();
                
                //add fixed row col section
                lc.ft_rel_container
                    .prepend($(cfg.tableTmpl(), {'class': 'ft_rc ui-widget-header'})
                    .append(theadTrClone));
                
                //an instance of fixed row column
                lc.ft_rc = $('.ft_rc', lc.ft_rel_container);
                
                //now clone the fixed row column and append tbody for the remaining rows
                lc.ft_c = lc.ft_rc.clone();
                lc.ft_c[0].className = 'ft_c';
                
                //append tbody
                lc.ft_c.append('<tbody />');
                
                //append row by row while just keeping the frozen cols
                var ftc_tbody = lc.ft_c.find('tbody'); 
                $.each ($this.find('tbody > tr'), function (idx, el) {
                    var tr = $(el).clone();
                    
                    tdct = 0;
                    tr.find('td').filter(function (){
                        tdct += this.colSpan;
                        return tdct > r1c1ColSpan;
                    }).remove();
                    
                    ftc_tbody.append(tr);
                });
                
                lc.ft_rc.after(lc.ft_c);
                lc.ft_c.wrap($('<div />', {'class': 'ft_cwrapper'}));

                var tw = 0;
                for (var i = 0; i < cfg.fixedCols; i++) {
                    tw += $(this.rows[0].cells[i]).outerWidth(true);
                }
                lc.ft_c.add(lc.ft_rc).width(tw);       
                lc.ft_c.height($this.outerHeight(true));
                    
                //set height of fixed_rc and fixed_c
                for (var i = 0; i < this.rows.length; i++) {
                    var ch = $(this.rows[i]).outerHeight();
                    var fch = $(lc.ft_c[0].rows[i]).outerHeight(true);
                    
                    ch = (ch>fch)?ch:fch;
                    
                    if (i < lc.ft_rc[0].rows.length) {
                        $(lc.ft_r[0].rows[i])
                            .add(lc.ft_rc[0].rows[i])                               
                            .height(ch);
                    }
                    
                    $(lc.ft_c[0].rows[i])
                        .add(this.rows[i])
                        .height(ch);
                }
                
                lc.ft_c         
                    .parent()
                    .css({height: lc.ft_container.height() - 17})
                    .width(lc.ft_rc.outerWidth(true) + 1);
            }       

            lc.ft_r
                .parent()
                .css({width: lc.ft_wrapper.width()- 17});
            
            //events (scroll and resize)
            lc.ft_wrapper.scroll(function () {
                if (cfg.fixedCols > 0) { 
                    lc.ft_c.css('top', ($(this).scrollTop()*-1));
                }
                lc.ft_r.css('left', ($(this).scrollLeft()*-1));
            });
            
            /*$(window).on('resize', function () {
                lc.ft_r
                .parent()
                .css({width: lc.ft_rel_container.width()- 17});         
            });*/
            
            if (cfg.sort && sorttable && cfg.fixedCols == 0) {
                
                $('table', lc.ft_container).addClass('sorttable');
                
                sorttable.makeSortable(this);
                
                var $sortableTh = $('.fx_sort_bg', lc.ft_rel_container);
                
                $sortableTh.click (function () {
                    var $this = $(this);
                    var isAscSort = $this.hasClass('fx_sort_asc'); 
                    
                    $sortableTh.removeClass('fx_sort_asc fx_sort_desc');
                    
                    if (isAscSort) { 
                        $this.addClass('fx_sort_desc').removeClass('fx_sort_asc'); 
                    } else { 
                        $this.addClass('fx_sort_asc').removeClass('fx_sort_desc'); 
                    }
                    
                    var idx = $(this).index();
                    
                    sorttable.innerSortFunction.apply(lc.ft_wrapper.find('th').get(idx), []);
                });
            }

        });

    };  

})(jQuery);
