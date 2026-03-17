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
                      if (window.console && console.error) {
                          console.error('Failed to initialize barcode scanner:', err);
                      }
                      if (typeof this.handleScannerError === 'function') {
                          this.handleScannerError(err);
                      }
                      return;
                  }
                  Quagga.start();
              }.bind(this));
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
        handleScannerError: function(err) {
            // Restore UI so the user can retry scanning
            this.hideOverlay();
            this.attachListeners();

            // Try to show an inline error message if an element is available
            var errorElement = document.querySelector('.scanner-error');
            var message = 'Unable to start the barcode scanner. ' +
                          'Please check your camera permissions and try again.';
            if (errorElement) {
                errorElement.textContent = message;
                errorElement.style.display = 'block';
            } else {
                // Fallback to an alert if no error container exists
                alert(message);
            }
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