/**
 * Crypto Utility - Client-side HMAC-SHA256 Request Signing
 * 
 * This module provides request signing functionality for secure API communication:
 * - HMAC-SHA256 signature generation
 * - Timestamp and nonce generation
 * - Request signing for API calls
 */

const SIGNING_KEY_STORAGE = 'phishcatcher_signing_key';
const TIMESTAMP_TOLERANCE = 300; // 5 minutes

export async function hmacSha256(message, key) {
    const encoder = new TextEncoder();
    const keyData = encoder.encode(key);
    const messageData = encoder.encode(message);
    
    const cryptoKey = await crypto.subtle.importKey(
        'raw',
        keyData,
        { name: 'HMAC', hash: 'SHA-256' },
        false,
        ['sign']
    );
    
    const signature = await crypto.subtle.sign('HMAC', cryptoKey, messageData);
    const hashArray = Array.from(new Uint8Array(signature));
    return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
}

export function generateTimestamp() {
    return Math.floor(Date.now() / 1000).toString();
}

export function generateNonce() {
    return crypto.randomUUID();
}

export async function signRequest(method, path, body, signingKey) {
    if (!signingKey) {
        return null;
    }
    
    const timestamp = generateTimestamp();
    const nonce = generateNonce();
    const bodyString = typeof body === 'string' ? body : JSON.stringify(body || '');
    const payload = `${method.toUpperCase()}:${path}:${timestamp}:${bodyString}`;
    
    const signature = await hmacSha256(payload, signingKey);
    
    return {
        signature,
        timestamp,
        nonce,
    };
}

export function storeSigningKey(key) {
    localStorage.setItem(SIGNING_KEY_STORAGE, key);
}

export function getSigningKey() {
    return localStorage.getItem(SIGNING_KEY_STORAGE);
}

export function clearSigningKey() {
    localStorage.removeItem(SIGNING_KEY_STORAGE);
}

export function generateClientSigningKey() {
    const array = new Uint8Array(32);
    crypto.getRandomValues(array);
    return Array.from(array, byte => byte.toString(16).padStart(2, '0')).join('');
}

export function validateTimestamp(timestamp) {
    const now = Math.floor(Date.now() / 1000);
    const diff = Math.abs(now - parseInt(timestamp, 10));
    return diff <= TIMESTAMP_TOLERANCE;
}
