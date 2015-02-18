function getSource(e)
{
    var targ;
    var event;
    if (!e) 
    {
        event = window.event;
    }
    else 
    {
        event = e;
    }
    if (event.target) 
    {
        targ = event.target;
    }
    else if (event.srcElement) 
    {
        targ = event.srcElement;
    }
    if (targ.nodeType == 3) // defeat Safari bug
    {
        targ = targ.parentNode;
    }
    var tname;
    tname=targ.tagName;
    return targ;
}

function deleteFieldEvent(event)
{
    targ = getSource(event);
    p = targ.parentNode;
    deleteField(p);
}

function deleteField(p)
{
    var i = 0;
    for (i = 0; i < p.childNodes.length; ++i) {
        if (p.childNodes[i].tagName == "SELECT") {
            p.childNodes[i].selectedIndex = 0;
        }
        else if (p.childNodes[i].tagName == "INPUT" && p.childNodes[i].type == "text") {
            p.childNodes[i].value = "";
        }
    }
}

function addField(type)
{
    form = document.getElementById("id_{{ wizard.steps.step0 }}-form_div");
    console.log(form.getElementsByTagName("p"));
    toCopy = form.getElementsByTagName("p")[0]


    var i = 0;
    for (i = 0; i < 3; ++i) {
        form.appendChild(toCopy.cloneNode(true));
        toCopy = toCopy.nextSibling
    }
    allP = form.getElementsByTagName("p");
    newP = allP[allP.length - 1];
    deleteField(newP);
    num_fields = 1 + parseInt(document.getElementById("id_{{ wizard.steps.step0 }}-num_"+type.substring(0, type.length-1)+"s").value);
    document.getElementById("id_{{ wizard.steps.step0 }}-num_"+type.substring(0, type.length-1)+"s").value = num_fields;
    var i = 0;
    for (i = 0; i < newP.childNodes.length; ++i) {
        if (newP.childNodes[i].tagName == "SELECT" || (newP.childNodes[i].tagName == "INPUT" && p.childNodes[i].type == "text")) {
            oldName = newP.childNodes[i].attributes['name'].value;
            indexOfStartNum = oldName.indexOf(type) + type.length;
            indexOfEndNum = oldName.indexOf(type) + type.length;
            var j = indexOfStartNum;
            for (; oldName.charAt(j) >= '0' && oldName.charAt(j) <= '9'; ++j) {
                indexOfEndNum = j;
            }
            newP.childNodes[i].attributes['name'].value = oldName.substring(0, indexOfStartNum) + num_fields + oldName.substring(indexOfEndNum+1);
            newP.childNodes[i].id = "id_" + newP.childNodes[i].attributes['name'].value;
        }
    }
}
