/**
 * Authentication Forms Enhancement
 * Adds password toggle, strength meter, and real-time validation
 */

(function() {
  'use strict';

  class AuthFormEnhancer {
    constructor() {
      this.init();
    }

    init() {
      if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => this.setup());
      } else {
        this.setup();
      }
    }

    setup() {
      this.enhancePasswordFields();
      this.addPasswordStrengthMeter();
      this.addRealTimeValidation();
      this.enhanceFormSubmission();
    }

    enhancePasswordFields() {
      const passwordInputs = document.querySelectorAll('input[type="password"]');
      
      passwordInputs.forEach(input => {
        if (input.parentElement.classList.contains('password-input-wrapper')) {
          return;
        }

        const wrapper = document.createElement('div');
        wrapper.className = 'password-input-wrapper';
        input.parentNode.insertBefore(wrapper, input);
        wrapper.appendChild(input);

        const toggleBtn = document.createElement('button');
        toggleBtn.type = 'button';
        toggleBtn.className = 'password-toggle';
        toggleBtn.setAttribute('aria-label', 'Show password');
        toggleBtn.innerHTML = `
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
            <circle cx="12" cy="12" r="3"></circle>
          </svg>
        `;

        wrapper.appendChild(toggleBtn);

        toggleBtn.addEventListener('click', () => {
          const type = input.type === 'password' ? 'text' : 'password';
          input.type = type;
          toggleBtn.setAttribute('aria-label', type === 'password' ? 'Show password' : 'Hide password');
          
          if (type === 'text') {
            toggleBtn.innerHTML = `
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
                <line x1="1" y1="1" x2="23" y2="23"></line>
              </svg>
            `;
          } else {
            toggleBtn.innerHTML = `
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                <circle cx="12" cy="12" r="3"></circle>
              </svg>
            `;
          }
        });
      });
    }

    addPasswordStrengthMeter() {
      const passwordInputs = document.querySelectorAll('input[name="password"], input[name="newpasswd"]');
      
      passwordInputs.forEach(input => {
        if (input.name.includes('confirm') || input.name.includes('again')) {
          return;
        }

        const container = document.createElement('div');
        container.className = 'password-strength-container';
        container.innerHTML = `
          <div class="password-strength-meter">
            <div class="password-strength-bar"></div>
          </div>
          <p class="password-strength-text"></p>
          <p class="password-strength-hint"></p>
        `;

        const wrapper = input.closest('.password-input-wrapper') || input.parentElement;
        wrapper.parentNode.insertBefore(container, wrapper.nextSibling);

        input.addEventListener('input', (e) => {
          this.updatePasswordStrength(e.target.value, container);
        });
      });
    }

    updatePasswordStrength(password, container) {
      const bar = container.querySelector('.password-strength-bar');
      const text = container.querySelector('.password-strength-text');
      const hint = container.querySelector('.password-strength-hint');

      if (!password) {
        bar.style.width = '0%';
        bar.className = 'password-strength-bar';
        text.textContent = '';
        hint.textContent = '';
        return;
      }

      const strength = this.calculatePasswordStrength(password);
      const widths = [0, 25, 50, 75, 100];
      const classes = ['', 'strength-weak', 'strength-weak', 'strength-medium', 'strength-strong'];
      const labels = ['', 'Weak', 'Fair', 'Good', 'Strong'];
      const hints = [
        '',
        '💡 Add uppercase letters, numbers, and symbols',
        '💡 Add more characters and symbols',
        '💡 Add special characters for better security',
        '✅ Excellent password!'
      ];

      bar.style.width = widths[strength] + '%';
      bar.className = 'password-strength-bar ' + classes[strength];
      text.className = 'password-strength-text ' + classes[strength];
      text.textContent = labels[strength];
      hint.textContent = hints[strength];
    }

    calculatePasswordStrength(password) {
      let strength = 0;
      
      if (password.length >= 8) strength++;
      if (password.length >= 12) strength++;
      if (/[a-z]/.test(password) && /[A-Z]/.test(password)) strength++;
      if (/\d/.test(password)) strength++;
      if (/[^a-zA-Z0-9]/.test(password)) strength++;
      
      return Math.min(strength, 4);
    }

    addRealTimeValidation() {
      const usernameInput = document.getElementById('id_username');
      if (usernameInput) {
        usernameInput.addEventListener('blur', () => {
          this.validateUsername(usernameInput);
        });
      }

      const emailInput = document.getElementById('id_email');
      if (emailInput) {
        emailInput.addEventListener('blur', () => {
          this.validateEmail(emailInput);
        });
      }

      const passwordInput = document.querySelector('input[name="password"]');
      const confirmInput = document.querySelector('input[name="password2"], input[name="newpasswdconfirm"]');
      
      if (passwordInput && confirmInput) {
        confirmInput.addEventListener('input', () => {
          this.validatePasswordMatch(passwordInput, confirmInput);
        });
      }
    }

    validateUsername(input) {
      const value = input.value.trim();
      const pattern = /^[\w.@+-]+$/;
      
      if (!value) {
        this.clearValidation(input);
        return;
      }
      
      if (pattern.test(value)) {
        this.setValid(input);
      } else {
        this.setInvalid(input, 'Username can only contain letters, numbers, and @/./+/-/_ characters');
      }
    }

    validateEmail(input) {
      const value = input.value.trim();
      const pattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      
      if (!value) {
        this.clearValidation(input);
        return;
      }
      
      if (pattern.test(value)) {
        this.setValid(input);
      } else {
        this.setInvalid(input, 'Please enter a valid email address');
      }
    }

    validatePasswordMatch(passwordInput, confirmInput) {
      const password = passwordInput.value;
      const confirm = confirmInput.value;
      
      if (!confirm) {
        this.clearValidation(confirmInput);
        return;
      }
      
      if (password === confirm) {
        this.setValid(confirmInput, 'Passwords match');
      } else {
        this.setInvalid(confirmInput, 'Passwords do not match');
      }
    }

    setValid(input, message = '') {
      input.classList.remove('is-invalid');
      input.classList.add('is-valid');
      this.removeFeedback(input);
      
      if (message) {
        const feedback = document.createElement('div');
        feedback.className = 'valid-feedback';
        feedback.textContent = message;
        input.parentElement.appendChild(feedback);
      }
    }

    setInvalid(input, message) {
      input.classList.remove('is-valid');
      input.classList.add('is-invalid');
      this.removeFeedback(input);
      
      const feedback = document.createElement('div');
      feedback.className = 'invalid-feedback';
      feedback.textContent = message;
      input.parentElement.appendChild(feedback);
    }

    clearValidation(input) {
      input.classList.remove('is-valid', 'is-invalid');
      this.removeFeedback(input);
    }

    removeFeedback(input) {
      const parent = input.parentElement;
      const feedback = parent.querySelector('.invalid-feedback, .valid-feedback');
      if (feedback) {
        feedback.remove();
      }
    }

    enhanceFormSubmission() {
      const forms = document.querySelectorAll('form');
      
      forms.forEach(form => {
        form.addEventListener('submit', (e) => {
          const submitBtn = form.querySelector('input[type="submit"], button[type="submit"]');
          
          if (submitBtn && !submitBtn.classList.contains('btn-loading')) {
            const originalText = submitBtn.value || submitBtn.textContent;
            submitBtn.classList.add('btn-loading');
            submitBtn.disabled = true;
            
            if (submitBtn.tagName === 'INPUT') {
              submitBtn.value = 'Please wait...';
            } else {
              submitBtn.textContent = 'Please wait...';
            }
            
            setTimeout(() => {
              submitBtn.classList.remove('btn-loading');
              submitBtn.disabled = false;
              if (submitBtn.tagName === 'INPUT') {
                submitBtn.value = originalText;
              } else {
                submitBtn.textContent = originalText;
              }
            }, 10000);
          }
        });
      });
    }
  }

  new AuthFormEnhancer();
})();
