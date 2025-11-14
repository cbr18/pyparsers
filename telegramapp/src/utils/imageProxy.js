/**
 * Utility functions for handling image URLs through proxy
 */

/**
 * List of domains that require proxy due to CORS issues
 */
const PROBLEMATIC_DOMAINS = [
  'autoimg.cn',
  'img.autoimg.cn',
  'pic.autoimg.cn',
  '2sc2.autoimg.cn',  // Добавлен поддомен из лога
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
  
  // Encode original URL so query params (e.g. x-signature) are preserved
  const encodedUrl = encodeURIComponent(originalUrl);
  return `/proxy-image?url=${encodedUrl}`;
};

/**
 * Check if an image URL should use proxy
 * @param {string} url - The URL to check
 * @returns {boolean} - True if should use proxy
 */
export const shouldUseProxy = (url) => {
  return isExternalUrl(url) && isProblematicDomain(url);
};
