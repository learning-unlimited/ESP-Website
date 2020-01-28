function setupDatepickerDurationLabel(widget, id, mediaUrl, dateFormat, timeFormat){
  var $picker = $j("#" + id);
  var $info = $j("#" + id + "-info");
  var $gi = $j("#" + id + "-gi");
  var $duration = $j("#" + id + "-duration");
  function refresh() {
    var date = $picker[widget]('getDate');
    if (date) {
      var hours = (date - Date.now()) / (60*60*1000);
      var abshours = Math.abs(hours);
      var duration = (abshours < 24) ? (
        abshours.toFixed(1) + " hours"
      ) : (
        (abshours / 24).toFixed(1) + " days"
      );
      if (abshours > 24 * 120) {
        $info.prop('class', 'label label-important');
        $gi.prop('class', 'glyphicon glyphicon-alert');
      } else {
        $info.prop('class', 'label label-info');
        if (hours < 0) {
          $gi.prop('class', 'glyphicon glyphicon-backward');
        } else {
          $gi.prop('class', 'glyphicon glyphicon-forward');
        }
      }
      $duration.text(hours < 0 ? (duration + " ago") : ("in " + duration));
      $info.show();
    } else {
      $info.hide();
    }
  }
  $picker[widget]({
    showOn: 'button',
      buttonImage: mediaUrl + 'images/calbutton_tight.png',
      buttonImageOnly: true,
      dateFormat: dateFormat,
      timeFormat: timeFormat,
  }).on("change", refresh);
  refresh();
}
