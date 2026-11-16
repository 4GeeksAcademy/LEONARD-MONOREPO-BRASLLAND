import {
  apiRequest, endSession, getToken, sessionFetch as authenticatedFetch, TOKEN_KEY,
} from '../../../packages/shared/auth/session.ts';
import {
  clearTelemetrySession, getSessionEndProperties, initializeTelemetry, track,
} from './services/telemetry.js';

function safeEndpoint(url) {
  return new URL(url, window.location.origin).pathname
    .replace(/\/(?:\d+|[0-9a-f]{8}-[0-9a-f-]{27,})(?=\/|$)/gi, '/:id');
}

export async function sessionFetch(url, init = {}, protectedCall = true) {
  const requestId = crypto.randomUUID();
  const headers = new Headers(init.headers);
  headers.set('X-Request-ID', requestId);
  const startedAt = performance.now();
  let statusCode = 0;
  try {
    const response = await authenticatedFetch(url, { ...init, headers }, protectedCall);
    statusCode = response.status;
    return response;
  } catch (error) {
    statusCode = Number.isInteger(error?.status) ? error.status : 0;
    if (protectedCall && statusCode === 401) {
      track('session_expired', getSessionEndProperties('timeout'));
    }
    throw error;
  } finally {
    track('api_request_completed', {
      endpoint: safeEndpoint(url),
      method: (init.method ?? 'GET').toUpperCase(),
      statusCode,
      durationMs: Math.max(0, Math.round(performance.now() - startedAt)),
    }, requestId);
  }
}

export async function requireSession() {
  if (!getToken()) {
    endSession();
    return false;
  }
  try {
    const user = await apiRequest('/api/backend/auth/me');
    initializeTelemetry(user);
    document.body.hidden = false;
    document.getElementById('logout').addEventListener('click', () => {
      track('session_expired', getSessionEndProperties('user_logout'));
      clearTelemetrySession();
      endSession();
    });
    window.addEventListener('storage', event => {
      if ((event.key === TOKEN_KEY || event.key === null) && !getToken()) {
        track('session_expired', getSessionEndProperties('user_logout'));
        clearTelemetrySession();
        endSession();
      }
      else if (event.key === TOKEN_KEY) window.location.reload();
    });
    return true;
  } catch (error) {
    if (error.status === 401) return false;
    document.body.replaceChildren();
    document.body.hidden = false;
    const message = document.createElement('p');
    message.textContent = 'Cannot verify your session. Please retry.';
    const retry = document.createElement('button');
    retry.textContent = 'Retry';
    retry.addEventListener('click', () => window.location.reload());
    document.body.append(message, retry);
    return false;
  }
}