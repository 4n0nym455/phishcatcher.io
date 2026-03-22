/**
 * UUID Utility Functions
 * 
 * Simple UUID v4 generator for client-side use
 * Note: For production, consider using a proper UUID library
 */

/**
 * Generate a random UUID v4
 * @returns {string} UUID v4 string
 */
export function generateUUID() {
  // Create a random UUID v4
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0;
    const v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
}

/**
 * Generate multiple UUIDs
 * @param {number} count - Number of UUIDs to generate
 * @returns {string[]} Array of UUIDs
 */
export function generateUUIDs(count) {
  return Array.from({ length: count }, () => generateUUID());
}

/**
 * Validate if a string is a valid UUID v4
 * @param {string} uuid - UUID string to validate
 * @returns {boolean} True if valid UUID v4
 */
export function isValidUUID(uuid) {
  const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
  return uuidRegex.test(uuid);
}

/**
 * Generate a short UUID (first 8 characters) for display purposes
 * @param {string} uuid - Full UUID
 * @returns {string} Short UUID
 */
export function shortUUID(uuid) {
  return uuid ? uuid.split('-')[0] : '';
}

/**
 * Create a URL-friendly slug from UUID (for use in URLs)
 * @param {string} uuid - UUID
 * @returns {string} URL-safe UUID (removes dashes)
 */
export function urlSafeUUID(uuid) {
  return uuid ? uuid.replace(/-/g, '') : '';
}

export default {
  generateUUID,
  generateUUIDs,
  isValidUUID,
  shortUUID,
  urlSafeUUID
};
