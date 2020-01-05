var App;
$j(function() {
    App = {
        init: function() {
            this.attachListeners();
        },
        attachListeners: function() {
            var button = document.querySelector('button.scan'),
                self = this;

            button.addEventListener("click", function clickListener (e) {
                e.preventDefault();
                button.removeEventListener("click", clickListener);
                self.activateScanner();
                audioCtx.resume();
            });
        },
        activateScanner: function() {
            var scanner = this.configureScanner('.overlay__content'),
                onDetected = function (result) {
                    this.addToResults(result);
                }.bind(this),
                stop = function() {
                    Quagga.stop();
                    this.hideOverlay();
                    this.attachListeners();
                }.bind(this);

            this.showOverlay(stop);
            var video = document.querySelector('.overlay__content > video');
            video.setAttribute("autoplay", true);
            video.setAttribute('muted', true);
            video.setAttribute('playsinline', true);
            $j(video).on("playing", function() {
                $j(".overlay").width($j('.overlay__content > video').width());
                $j('.overlay__close').show();
            });
        },
        configureScanner: function(selector) {
            var scanner = Quagga.init({
                decoder: {
                    readers: this.querySelectedReaders()
                },
                inputStream: {
                    type : "LiveStream",
                    constraints: {
                        width: 500,
                        height: {},
                        facingMode: "environment",
                        aspectRatio: {min: 1, max: 2}
                    }
                },
            }, function(err) {
                  if (err) {
                      console.log(err);
                      return
                  }
                  Quagga.start();
              });
            return scanner;
        },
        querySelectedReaders: function() {
            return Array(document.querySelector('.controls select').value);
        },
        showOverlay: function(cancelCb) {
            document.querySelector('.controls')
                .classList.add('hide');
            document.querySelector('.overlay--inline')
                .classList.add('show');
            var closeButton = document.querySelector('.overlay__close');
            closeButton.addEventListener('click', function closeHandler() {
                closeButton.removeEventListener("click", closeHandler);
                cancelCb();
                $j(closeButton).hide();
            });
        },
        hideOverlay: function() {
            document.querySelector('.controls')
                .classList.remove('hide');
            document.querySelector('.overlay--inline')
                .classList.remove('show');
        },
        lastResult : null
    };

    App.init();
});

audioCtx = new (window.AudioContext || window.webkitAudioContext)();

function beep() {
    var oscillator = audioCtx.createOscillator();
    var gainNode = audioCtx.createGain();

    oscillator.connect(gainNode);
    gainNode.connect(audioCtx.destination);

    gainNode.gain.value = 1;
    oscillator.frequency.value = 3000;
    oscillator.type = 'sine';

    oscillator.start();
  
    setTimeout(
      function(){
        oscillator.stop();
      }, 
      150
    );  
};