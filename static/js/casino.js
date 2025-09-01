/**
 * Casino Game System - Core JavaScript
 * Модульная система для казино
 */

class CasinoSystem {
  constructor() {
    this.eventListeners = {};
    this.modules = {};
    this.init();
  }

  init() {
    // Инициализация основных компонентов
    document.addEventListener('DOMContentLoaded', () => {
      this.initNavigation();
      this.dispatchEvent('system:ready', {});
    });
  }

  // Инициализация навигационного меню
  initNavigation() {
    const toggle = document.getElementById('navToggle');
    const menu = document.getElementById('navMenu');

    if (toggle && menu) {
      toggle.addEventListener('click', () => {
        menu.classList.toggle('active');
        toggle.classList.toggle('active');
      });

      // Закрытие меню при клике вне его
      document.addEventListener('click', (e) => {
        if (!e.target.closest('.nav-menu') && !e.target.closest('.nav-toggle')) {
          menu.classList.remove('active');
          toggle.classList.remove('active');
        }
      });
    }
  }

  // Система событий
  addEventListener(eventName, callback) {
    if (!this.eventListeners[eventName]) {
      this.eventListeners[eventName] = [];
    }
    this.eventListeners[eventName].push(callback);
    return this;
  }

  dispatchEvent(eventName, data) {
    if (this.eventListeners[eventName]) {
      this.eventListeners[eventName].forEach(callback => callback(data));
    }
    return this;
  }

  // Система модулей
  registerModule(moduleName, moduleInstance) {
    this.modules[moduleName] = moduleInstance;
    this.dispatchEvent('module:registered', { name: moduleName, instance: moduleInstance });
    return this;
  }

  getModule(moduleName) {
    return this.modules[moduleName];
  }

  // Утилиты
  showToast(message, type = 'info', duration = 3000) {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;

    const container = document.querySelector('.toast-container') || (() => {
      const newContainer = document.createElement('div');
      newContainer.className = 'toast-container';
      document.body.appendChild(newContainer);
      return newContainer;
    })();

    container.appendChild(toast);

    setTimeout(() => {
      toast.classList.add('show');
    }, 10);

    setTimeout(() => {
      toast.classList.remove('show');
      setTimeout(() => toast.remove(), 300);
    }, duration);
  }

  // Анимации и эффекты
  animateNumber(element, start, end, duration = 1000, decimals = 0) {
    if (!element) return;

    const startTime = performance.now();
    const updateNumber = (currentTime) => {
      const elapsedTime = currentTime - startTime;
      const progress = Math.min(elapsedTime / duration, 1);
      const easedProgress = this.easeOutCubic(progress);
      const currentValue = start + (end - start) * easedProgress;

      element.textContent = currentValue.toFixed(decimals);

      if (progress < 1) {
        requestAnimationFrame(updateNumber);
      }
    };

    requestAnimationFrame(updateNumber);
  }

  easeOutCubic(x) {
    return 1 - Math.pow(1 - x, 3);
  }
}

// Инициализация Casino System
const casinoSystem = new CasinoSystem();

// Экспорт для глобального доступа
window.casinoSystem = casinoSystem;
