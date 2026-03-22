/**
 * Semantic URL Utilities
 * 
 * Provides functions for creating meaningful, SEO-friendly URLs
 * throughout the PhishCatcher application
 */

import { format } from 'date-fns';

/**
 * Generate a meaningful slug from analysis data
 */
export const createAnalysisSlug = (analysis) => {
  if (!analysis) return '';
  
  const timestamp = new Date(analysis.analyzedAt || analysis.receivedAt);
  const dateStr = format(timestamp, 'yyyy-MM-dd');
  const timeStr = format(timestamp, 'HH-mm');
  
  // Create descriptive slug based on analysis type and content
  const typePrefix = analysis.category?.toLowerCase() || 'analysis';
  const subjectSlug = analysis.subject
    .toLowerCase()
    .replace(/[^a-z0-9\s-]/g, '-')
    .substring(0, 50);
  
  return `${dateStr}-${timeStr}-${typePrefix}-${subjectSlug}`;
};

/**
 * Generate UUID-based URL (most secure)
 */
export const createAnalysisUrl = (analysis) => {
  if (!analysis || !analysis.id) return '#';
  
  // Use the existing ID if it's already a UUID or meaningful string
  if (typeof analysis.id === 'string' && analysis.id.length > 8) {
    return `/analysis/${analysis.id}`;
  }
  
  // For numeric IDs, create semantic slug
  return `/analysis/${createAnalysisSlug(analysis)}`;
};

/**
 * Create email upload URL with session ID
 */
export const createUploadUrl = (sessionId) => {
  return `/upload/${sessionId}`;
};

/**
 * Create admin URLs with proper structure
 */
export const createAdminUrl = (section, item) => {
  if (!section) return '/admin';
  if (!item) return `/admin/${section}`;
  
  return `/admin/${section}/${item}`;
};

/**
 * Create user settings URLs
 */
export const createSettingsUrl = (section) => {
  if (!section) return '/settings';
  return `/settings/${section}`;
};

/**
 * Create weekly report URL with date range
 */
export const createWeeklyReportUrl = (startDate, endDate) => {
  const start = format(new Date(startDate), 'yyyy-MM-dd');
  const end = format(new Date(endDate), 'yyyy-MM-dd');
  return `/weekly-reports/${start}-to-${end}`;
};

/**
 * Create search results URL with query parameters
 */
export const createSearchUrl = (query, filters = {}) => {
  const params = new URLSearchParams();
  
  if (query) params.set('q', query);
  if (filters.status) params.set('status', filters.status);
  if (filters.type) params.set('type', filters.type);
  if (filters.date) params.set('date', filters.date);
  
  const queryString = params.toString();
  return queryString ? `/analysis?${queryString}` : '/analysis';
};

/**
 * Validate if a URL is a valid analysis URL
 */
export const isValidAnalysisUrl = (url) => {
  return /^\/analysis\/[a-zA-Z0-9\-_]+$/.test(url) || 
         /^\/analysis\/[0-9a-f]{8}-[0-9a-f]{4}-[0-9]{2}-[a-z0-9\-_]+$/.test(url);
};

/**
 * Extract analysis ID from URL
 */
export const extractAnalysisId = (url) => {
  const match = url.match(/^\/analysis\/(.+)$/);
  return match ? match[1] : null;
};

/**
 * Create breadcrumb navigation items
 */
export const createBreadcrumb = (currentPath, analysis) => {
  const items = [
    { label: 'Dashboard', href: '/dashboard' },
    { label: 'Analysis History', href: '/analysis' },
  ];
  
  if (analysis && analysis.id) {
    items.push({ 
      label: analysis.subject?.substring(0, 30) + (analysis.subject?.length > 30 ? '...' : ''), 
      href: createAnalysisUrl(analysis),
      current: true 
    });
  }
  
  return items;
};

/**
 * URL patterns for validation
 */
export const URL_PATTERNS = {
  ANALYSIS: /^\/analysis\/[a-zA-Z0-9\-_]+$/,
  UPLOAD: /^\/upload\/[a-zA-Z0-9\-_]*$/,
  ADMIN: /^\/admin\/[a-zA-Z0-9\-_\/]+$/,
  SETTINGS: /^\/settings\/[a-zA-Z0-9\-_\/]+$/,
  WEEKLY_REPORTS: /^\/weekly-reports\/[0-9]{4}-to-[0-9]{4}$/,
};

export default {
  createAnalysisSlug,
  createAnalysisUrl,
  createUploadUrl,
  createAdminUrl,
  createSettingsUrl,
  createWeeklyReportUrl,
  createSearchUrl,
  isValidAnalysisUrl,
  extractAnalysisId,
  createBreadcrumb,
  URL_PATTERNS,
};
