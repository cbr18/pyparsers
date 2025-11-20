/**
 * Utility functions for handling image URLs through proxy
 * 
 * ПОЧЕМУ ПРОКСИРУЕМ КАРТИНКИ:
 * 1. CORS - китайские CDN блокируют прямые запросы с других доменов
 * 2. Referer - многие CDN проверяют откуда идет запрос (hotlink protection)
 * 3. IP-блокировки - некоторые CDN блокируют запросы из России
 * 
 * ПОЧЕМУ НЕ ВСЕ:
 * - Подписанные URL (с x-signature) проверяют IP клиента и время
 * - Прокси меняет IP, подпись становится невалидной → 403 Forbidden
 * - Такие URL должны загружаться напрямую от клиента
 */

/**
 * List of domains that require proxy due to CORS/Referer issues
 */
const PROBLEMATIC_DOMAINS = [
  'autoimg.cn',       // che168 images (требуют referer: che168.com)
  'byteimg.com',      // dongchedi images (требуют referer: dongchedi.com)
  // Add other problematic domains here
];

/**
 * Check if a URL is external (not from our domain)
 * @param {string} url - The URL to check
 * @returns {boolean} - True if external, false if internal
 */
const isExternalUrl = (url) => {
  if (!url || typeof url !== 'string') return false;
  
  // Check if it's a data URL (base64 encoded image)
  if (url.startsWith('data:')) return false;
  
  // Check if it's a relative URL
  if (url.startsWith('/')) return false;
  
  // Check if it's from our domain
  const currentDomain = window.location.hostname;
  try {
    const urlObj = new URL(url);
    return urlObj.hostname !== currentDomain;
  } catch (e) {
    // If URL parsing fails, assume it's external
    return true;
  }
};

/**
 * Check if a URL is from a problematic domain that requires proxy
 * @param {string} url - The URL to check
 * @returns {boolean} - True if from problematic domain
 */
const isProblematicDomain = (url) => {
  if (!url || typeof url !== 'string') return false;
  
  // Подписанные URL dongchedi грузятся напрямую (подпись проверяет IP/время)
  if (url.includes('-sign.byteimg.com') && url.includes('x-signature')) {
    return false;
  }
  
  try {
    const urlObj = new URL(url);
    return PROBLEMATIC_DOMAINS.some(domain => 
      urlObj.hostname === domain || urlObj.hostname.endsWith('.' + domain)
    );
  } catch (e) {
    return false;
  }
};

/**
 * Convert external image URL to proxy URL
 * @param {string} originalUrl - The original image URL
 * @returns {string} - The proxied URL or original URL if not external
 */
export const getProxiedImageUrl = (originalUrl) => {
  if (!originalUrl || typeof originalUrl !== 'string') {
    return originalUrl;
  }
  
  // If it's not an external URL, return as is
  if (!isExternalUrl(originalUrl)) {
    return originalUrl;
  }
  
  // Only use proxy for problematic domains
  if (!isProblematicDomain(originalUrl)) {
    return originalUrl;
  }
  
  // Не кодируем URL вручную - браузер сделает это автоматически
  // Это предотвращает двойное кодирование (особенно для % в подписях)
  return `/proxy-image?url=${originalUrl}`;
};

/**
 * Check if an image URL should use proxy
 * @param {string} url - The URL to check
 * @returns {boolean} - True if should use proxy
 */
export const shouldUseProxy = (url) => {
  return isExternalUrl(url) && isProblematicDomain(url);
};
