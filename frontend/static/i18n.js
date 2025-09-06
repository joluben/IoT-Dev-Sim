/**
 * Sistema de Internacionalización (i18n) para Device Simulator
 * Soporta español (es) e inglés (en) con español como idioma por defecto
 */
class I18n {
  constructor() {
    this.currentLanguage = this.detectLanguage();
    this.translations = {};
    this.fallbackLanguage = 'en';
    this.loadedNamespaces = new Set();
    this.defaultLanguage = 'es'; // Español como idioma por defecto
  }
  
  /**
   * Detecta el idioma a usar basado en preferencias y configuración
   * Prioridad: localStorage > configuración por defecto (español)
   */
  detectLanguage() {
    // 1. Comprobar localStorage
    const stored = localStorage.getItem('preferred_language');
    if (stored && ['en', 'es'].includes(stored)) {
      return stored;
    }
    
    // 2. Usar español como idioma por defecto (según requerimiento)
    return this.defaultLanguage;
  }
  
  /**
   * Carga un namespace de traducciones de forma asíncrona
   * @param {string} namespace - Namespace a cargar (common, devices, etc.)
   */
  async loadNamespace(namespace) {
    const namespaceKey = `${this.currentLanguage}-${namespace}`;
    
    if (this.loadedNamespaces.has(namespaceKey)) {
      return;
    }
    
    try {
      const response = await fetch(`/locales/${this.currentLanguage}/${namespace}.json`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const translations = await response.json();
      
      if (!this.translations[this.currentLanguage]) {
        this.translations[this.currentLanguage] = {};
      }
      
      this.translations[this.currentLanguage][namespace] = translations;
      this.loadedNamespaces.add(namespaceKey);
      
      console.log(`✅ Loaded translations: ${this.currentLanguage}/${namespace}`);
      
    } catch (error) {
      console.warn(`⚠️ Failed to load translations for ${namespace} (${this.currentLanguage}):`, error);
      
      // Cargar fallback si no está disponible el idioma actual
      if (this.currentLanguage !== this.fallbackLanguage) {
        try {
          const fallbackResponse = await fetch(`/locales/${this.fallbackLanguage}/${namespace}.json`);
          if (fallbackResponse.ok) {
            const fallbackTranslations = await fallbackResponse.json();
            
            if (!this.translations[this.fallbackLanguage]) {
              this.translations[this.fallbackLanguage] = {};
            }
            
            this.translations[this.fallbackLanguage][namespace] = fallbackTranslations;
            console.log(`✅ Loaded fallback translations: ${this.fallbackLanguage}/${namespace}`);
          }
        } catch (fallbackError) {
          console.error(`❌ Failed to load fallback translations for ${namespace}:`, fallbackError);
        }
      }
    }
  }
  
  /**
   * Obtiene una traducción usando la notación de puntos
   * @param {string} key - Clave de traducción (ej: 'common.actions.save')
   * @param {object} options - Opciones para interpolación de variables
   * @returns {string} Texto traducido
   */
  t(key, options = {}) {
    const keys = key.split('.');
    const namespace = keys[0];
    const translationKey = keys.slice(1).join('.');
    
    // Buscar en idioma actual
    let translation = this.getTranslation(this.currentLanguage, namespace, translationKey);
    
    // Fallback a idioma por defecto
    if (!translation && this.currentLanguage !== this.fallbackLanguage) {
      translation = this.getTranslation(this.fallbackLanguage, namespace, translationKey);
    }
    
    // Fallback a la clave original si no se encuentra traducción
    if (!translation) {
      console.warn(`⚠️ Missing translation: ${key} (${this.currentLanguage})`);
      translation = key;
    }
    
    // Interpolación de variables
    return this.interpolate(translation, options);
  }
  
  /**
   * Obtiene una traducción específica de un idioma y namespace
   * @param {string} language - Código de idioma
   * @param {string} namespace - Namespace
   * @param {string} key - Clave de traducción
   * @returns {string|null} Traducción encontrada o null
   */
  getTranslation(language, namespace, key) {
    if (!this.translations[language] || !this.translations[language][namespace]) {
      return null;
    }
    
    return this.getNestedValue(this.translations[language][namespace], key);
  }
  
  /**
   * Obtiene un valor anidado de un objeto usando notación de puntos
   * @param {object} obj - Objeto donde buscar
   * @param {string} path - Ruta con puntos (ej: 'actions.save')
   * @returns {any} Valor encontrado o null
   */
  getNestedValue(obj, path) {
    return path.split('.').reduce((current, key) => {
      return current && current[key] !== undefined ? current[key] : null;
    }, obj);
  }
  
  /**
   * Interpola variables en un texto usando la sintaxis {{variable}}
   * @param {string} text - Texto con variables
   * @param {object} options - Variables para interpolación
   * @returns {string} Texto con variables reemplazadas
   */
  interpolate(text, options) {
    if (!options || typeof text !== 'string') {
      return text;
    }
    
    return text.replace(/\{\{([^}]+)\}\}/g, (match, key) => {
      const trimmedKey = key.trim();
      return options[trimmedKey] !== undefined ? options[trimmedKey] : match;
    });
  }
  
  /**
   * Cambia el idioma de la aplicación
   * @param {string} language - Código de idioma ('en' o 'es')
   */
  async changeLanguage(language) {
    if (!['en', 'es'].includes(language)) {
      throw new Error(`Unsupported language: ${language}`);
    }
    
    if (language === this.currentLanguage) {
      return; // No hay cambio
    }
    
    console.log(`🌐 Changing language from ${this.currentLanguage} to ${language}`);
    
    this.currentLanguage = language;
    localStorage.setItem('preferred_language', language);
    
    // Recargar todas las traducciones cargadas para el nuevo idioma
    const namespacesToReload = Array.from(this.loadedNamespaces)
      .map(item => item.split('-')[1])
      .filter((item, index, arr) => arr.indexOf(item) === index);
    
    // Limpiar namespaces cargados para forzar recarga
    this.loadedNamespaces.clear();
    
    // Cargar traducciones para el nuevo idioma
    for (const namespace of namespacesToReload) {
      await this.loadNamespace(namespace);
    }
    
    // Actualizar interfaz
    this.updateDOM();
    
    // Notificar cambio de idioma
    document.dispatchEvent(new CustomEvent('languageChanged', {
      detail: { 
        language,
        previousLanguage: this.currentLanguage 
      }
    }));
    
    console.log(`✅ Language changed to ${language}`);
  }
  
  /**
   * Actualiza todos los elementos del DOM con traducciones
   */
  updateDOM() {
    // Actualizar elementos con atributo data-i18n
    const elements = document.querySelectorAll('[data-i18n]');
    elements.forEach(element => {
      const key = element.getAttribute('data-i18n');
      const translation = this.t(key);
      
      if (element.tagName === 'INPUT' && (element.type === 'text' || element.type === 'search')) {
        element.placeholder = translation;
      } else {
        element.textContent = translation;
      }
    });
    
    // Actualizar elementos con atributo data-i18n-placeholder
    const placeholderElements = document.querySelectorAll('[data-i18n-placeholder]');
    placeholderElements.forEach(element => {
      const key = element.getAttribute('data-i18n-placeholder');
      element.placeholder = this.t(key);
    });
    
    // Actualizar selector de idioma
    this.updateLanguageSelector();
  }
  
  /**
   * Actualiza el selector de idioma en la UI
   */
  updateLanguageSelector() {
    const languageButton = document.getElementById('language-selector');
    if (languageButton) {
      const currentLangText = this.t('common.language.current');
      languageButton.innerHTML = `🌐 ${currentLangText}`;
      
      const switchText = this.t('common.language.switch_to');
      languageButton.title = switchText;
    }
  }
  
  /**
   * Inicializa el sistema de i18n cargando los namespaces básicos
   */
  async initialize() {
    console.log(`🚀 Initializing i18n system with language: ${this.currentLanguage}`);
    
    // Cargar namespaces básicos
    await Promise.all([
      this.loadNamespace('common'),
      this.loadNamespace('devices'),
      this.loadNamespace('connections'),
      this.loadNamespace('projects')
    ]);
    
    // Actualizar DOM inicial
    this.updateDOM();
    
    console.log(`✅ i18n system initialized`);
  }
  
  /**
   * Obtiene el idioma actual
   * @returns {string} Código del idioma actual
   */
  getCurrentLanguage() {
    return this.currentLanguage;
  }
  
  /**
   * Obtiene la lista de idiomas soportados
   * @returns {Array} Lista de códigos de idioma
   */
  getSupportedLanguages() {
    return ['es', 'en'];
  }
}

// Crear instancia global
window.i18n = new I18n();
