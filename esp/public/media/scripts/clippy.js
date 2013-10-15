/*
 * clippy.js
 * Creates Click-to-Copy Links
 *
 * 1. Create links like so:
 *      <i class="clippy" data-clipboard-target="id_of_some_element"></i>
 * 2. Link to this script inside of <head>:
 *      <script type="text/javascript" src="/media/scripts/clippy.js"></script>
 */

var clippy = {};
clippy.lastElement = '';
clippy.lastText = '';

(function(d, script) {
  // Determine Proper Linebreaks to Use
  linebreak = '\n';
  if (navigator.platform.toUpperCase().indexOf('WIN') >= 0) {
    linebreak = '\r\n';
  }
  
  // Load ZeroClipboard from CDN
  // http://stackoverflow.com/questions/8578617
  script = d.createElement('script');
  script.type = 'text/javascript';
  script.src = '/media/scripts/zeroclipboard/v1.1.7/ZeroClipboard.min.js';
  script.onload = function() {
    ZeroClipboard.setDefaults({
      moviePath: '/media/scripts/zeroclipboard/v1.1.7/ZeroClipboard.swf',
    });
    var icons = d.getElementsByClassName('clippy');
    for (var i = 0; i < icons.length; i++) {
      var e = icons[i];
      var clip = new ZeroClipboard(e);
      
      clip.on('dataRequested', function(client, args) {
        // Get Text to Copy to Clipboard
        var targetId = this.getAttribute('data-clippy-target');
        var target = document.getElementById(targetId);
        var text = target.innerHTML;
        text = text.replace(/<br[^>]*>/gi, linebreak);
        
        // If holding SHIFT, append to previously-copied text
        if (args.shiftKey && clippy.lastText.length > 0) {
          if (targetId == clippy.lastElement.replace(/-name/g, '-email')
             && targetId != clippy.lastElement) {
            // (name + email is formatted specially)
            text = clippy.lastText + ' <' + text + '>';
          }
          else {
            text = clippy.lastText + linebreak + text;
          }
          clippy.lastElement = 'multiple';
          clippy.lastText = text;
        }
        else {
          clippy.lastElement = targetId;
          clippy.lastText = text;
        }

        // ZeroClipboard can't actually empty the clipboard
        if (text == '') text = ' ';
        
        // Send to Clipboard!
        client.setText(text);
      });
      
      noFlashFunction = function(client, args) {
        e.className += ' noflash';
      };
      clip.on('noflash', noFlashFunction);
      clip.on('wrongflash', noFlashFunction);
      e.className += ' icon-paper-clip';
    }
  };
  d.getElementsByTagName('head')[0].appendChild(script);
  
  // Load FontAwesome from CDN
  stylesheet = d.createElement('link');
  stylesheet.rel = 'stylesheet';
  stylesheet.href = '//netdna.bootstrapcdn.com/font-awesome/3.2.1/css/font-awesome.css';
  d.getElementsByTagName('head')[0].appendChild(stylesheet);

  // Load ESP-specific CSS
  stylesheet = d.createElement('link');
  stylesheet.rel = 'stylesheet';
  stylesheet.href = '/media/styles/clippy.css';
  d.getElementsByTagName('head')[0].appendChild(stylesheet);
}(document));
