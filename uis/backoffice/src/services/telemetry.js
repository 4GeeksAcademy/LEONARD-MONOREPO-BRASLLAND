import eventSchemas from '../../../../docs/telemetry/event-schemas.json';

export const SCHEMA_VERSION = eventSchemas.version;

const ENDPOINT = process.env.NEXT_PUBLIC_TELEMETRY_ENDPOINT;
const MAX_BATCH_SIZE = 20;
const FLUSH_INTERVAL_MS = 10_000;
const MAX_RETRIES = 3;
const SESSION_ID_KEY = 'brasaland.telemetry.session_id';
const SESSION_USER_KEY = 'brasaland.telemetry.user_id';
const SESSION_STARTED_KEY = 'brasaland.telemetry.started_at';
const LAST_ACTIVITY_KEY = 'brasaland.telemetry.last_activity_at';
const definitions = new Map(eventSchemas.events.map(event => [event.event_type, event]));

let queue = [];
let currentUserId;
let currentSessionId;
let sessionStartedAt;
let lastActivityAt;
let flushPromise;
let inFlightBatch = [];
let inFlightSentWithBeacon = false;
let flushAfterCurrent = false;
let listenersInstalled = false;
const featureClickTimes = new Map();

function uuid() {
  return crypto.randomUUID();
}

function readSessionValue(key) {
  try {
    return sessionStorage.getItem(key);
  } catch (error) {
    console.warn('Telemetry session storage is unavailable.', error);
    return null;
  }
}

function writeSessionValue(key, value) {
  try {
    sessionStorage.setItem(key, value);
  } catch (error) {
    console.warn('Telemetry session storage is unavailable.', error);
  }
}

function validProperty(value, definition) {
  if (value === undefined || value === null) return !definition.required;
  if (definition.type === 'string' && typeof value !== 'string') return false;
  if (definition.type === 'integer' && !Number.isInteger(value)) return false;
  if (definition.type === 'number' && (typeof value !== 'number' || !Number.isFinite(value))) return false;
  if (definition.enum && !definition.enum.includes(value)) return false;
  return true;
}

function shouldSampleApiEvent(requestId) {
  let hash = 0;
  for (const character of requestId) hash = (hash * 31 + character.charCodeAt(0)) >>> 0;
  return hash % 10 === 0;
}

function shouldThrottlePageView(properties) {
  const key = `brasaland.telemetry.page_viewed:${properties.pageUrl}`;
  const now = Date.now();
  const previous = Number(readSessionValue(key));
  if (Number.isFinite(previous) && now - previous < 30_000) return true;
  writeSessionValue(key, String(now));
  return false;
}

function captureFrontendError(error) {
  track('service_error_occurred', {
    errorType: error instanceof Error ? error.name.slice(0, 100)
      : typeof error === 'string' ? 'FrontendError' : 'UnhandledRejection',
    errorMessage: 'Frontend error details omitted for privacy.',
    endpoint: location.pathname,
    severity: 'error',
  });
}

function flushWithBeacon() {
  if (!queue.length && !inFlightBatch.length) return;
  if (typeof navigator.sendBeacon !== 'function') {
    void flushQueue();
    return;
  }
  const events = inFlightSentWithBeacon ? [...queue] : [...inFlightBatch, ...queue];
  if (!events.length) return;
  try {
    const accepted = navigator.sendBeacon(
      ENDPOINT,
      new Blob([JSON.stringify({ events })], { type: 'application/json' }),
    );
    if (accepted) {
      queue = [];
      if (inFlightBatch.length) inFlightSentWithBeacon = true;
    } else if (!inFlightBatch.length) {
      void flushQueue();
    } else {
      flushAfterCurrent = true;
    }
  } catch (error) {
    console.warn('Telemetry beacon could not be sent; falling back to fetch.', error);
    if (!inFlightBatch.length) void flushQueue();
  }
}

async function flushQueue() {
  if (flushPromise) return flushPromise;
  if (!queue.length) return;

  inFlightBatch = queue.splice(0, MAX_BATCH_SIZE);
  inFlightSentWithBeacon = false;
  const payload = JSON.stringify({ events: inFlightBatch });
  flushPromise = (async () => {
    for (let attempt = 0; attempt <= MAX_RETRIES; attempt += 1) {
      try {
        const response = await fetch(ENDPOINT, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: payload,
          keepalive: true,
        });
        if (!response.ok) throw new Error(`Telemetry endpoint returned ${response.status}.`);
        return;
      } catch (error) {
        if (inFlightSentWithBeacon) return;
        if (attempt === MAX_RETRIES) {
          console.warn('Telemetry batch discarded after retries were exhausted.', error);
          return;
        }
        await new Promise(resolve => setTimeout(resolve, 500 * (2 ** attempt)));
      }
    }
  })().finally(() => {
    inFlightBatch = [];
    inFlightSentWithBeacon = false;
    flushPromise = undefined;
    const shouldFlushAgain = flushAfterCurrent || queue.length >= MAX_BATCH_SIZE;
    flushAfterCurrent = false;
    if (shouldFlushAgain && queue.length) void flushQueue();
  });
  return flushPromise;
}

function installListeners() {
  if (listenersInstalled) return;
  listenersInstalled = true;
  for (const eventName of ['pointerdown', 'keydown', 'touchstart']) {
    window.addEventListener(eventName, () => {
      lastActivityAt = Date.now();
      writeSessionValue(LAST_ACTIVITY_KEY, String(lastActivityAt));
    }, { passive: true });
  }
  window.addEventListener('error', event => {
    if (event instanceof ErrorEvent) captureFrontendError(event.error ?? event.message);
  });
  window.addEventListener('unhandledrejection', event => captureFrontendError(event.reason));
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'hidden') flushWithBeacon();
  });
  window.addEventListener('pagehide', () => {
    const pageUrl = location.pathname;
    const pageLocation = new URLSearchParams(location.search).get('location_id');
    const locationId = /^(COL-(0[1-9]|10)|FLA-0[1-4])$/.test(pageLocation ?? '') ? pageLocation : undefined;
    track('page_viewed', {
      pageUrl,
      pageTitle: document.title,
      locationId,
      timeOnPage: Math.max(0, Math.floor((Date.now() - pageStartedAt) / 1000)),
    });
    flushWithBeacon();
  }, { once: true });
  window.setInterval(() => { void flushQueue(); }, FLUSH_INTERVAL_MS);
}

let pageStartedAt = Date.now();

export function initializeTelemetry(user) {
  if (!user || typeof user.id !== 'string' || !user.id) {
    console.warn('Telemetry was not initialized because the authenticated user ID is unavailable.');
    return;
  }

  const storedUserId = readSessionValue(SESSION_USER_KEY);
  const storedSessionId = readSessionValue(SESSION_ID_KEY);
  const storedStartTime = Number(readSessionValue(SESSION_STARTED_KEY));
  const isNewSession = storedUserId !== user.id || !storedSessionId
    || !Number.isFinite(storedStartTime) || storedStartTime <= 0;
  currentUserId = user.id;
  currentSessionId = isNewSession ? uuid() : storedSessionId;
  sessionStartedAt = isNewSession ? Date.now() : storedStartTime;
  lastActivityAt = Number(readSessionValue(LAST_ACTIVITY_KEY)) || Date.now();
  pageStartedAt = Date.now();

  writeSessionValue(SESSION_USER_KEY, currentUserId);
  writeSessionValue(SESSION_ID_KEY, currentSessionId);
  writeSessionValue(SESSION_STARTED_KEY, String(sessionStartedAt));
  if (!readSessionValue(LAST_ACTIVITY_KEY)) writeSessionValue(LAST_ACTIVITY_KEY, String(lastActivityAt));

  if (isNewSession) {
    const roles = { user: 'operator', manager: 'manager', admin: 'admin' };
    track('session_created', {});
    track('user_login_successful', {
      userId: currentUserId,
      locationId: 'N/A',
      userRole: roles[user.role] ?? 'operator',
      authMethod: 'password',
    });
  }
  installListeners();
}

export function getSessionEndProperties(expiryReason) {
  const now = Date.now();
  const startedAt = Number.isFinite(sessionStartedAt) ? sessionStartedAt : now;
  const activeAt = Number.isFinite(lastActivityAt) ? lastActivityAt : now;
  return {
    sessionDurationSeconds: Math.max(0, Math.floor((now - startedAt) / 1000)),
    expiryReason,
    inactivityMinutes: Math.max(0, Math.floor((now - activeAt) / 60_000)),
  };
}

export function clearTelemetrySession() {
  for (const key of [SESSION_ID_KEY, SESSION_USER_KEY, SESSION_STARTED_KEY, LAST_ACTIVITY_KEY]) {
    try {
      sessionStorage.removeItem(key);
    } catch (error) {
      console.warn('Telemetry session storage is unavailable.', error);
      return;
    }
  }
}

export function track(eventType, properties, requestId = uuid()) {
  const definition = definitions.get(eventType);
  if (!definition || !currentUserId || !currentSessionId) {
    console.warn(`Telemetry event ${eventType} was not queued because its schema or session is unavailable.`);
    return;
  }
  if (eventType === 'api_request_completed' && !shouldSampleApiEvent(requestId)) return;

  const allowlist = new Set(definition.property_allowlist);
  const unexpected = Object.keys(properties).filter(key => !allowlist.has(key));
  if (unexpected.length) console.warn(`Ignored unapproved properties for telemetry event ${eventType}.`, unexpected);
  const safeProperties = Object.fromEntries(
    Object.entries(definition.properties)
      .filter(([key]) => allowlist.has(key) && properties[key] !== undefined)
      .map(([key]) => [key, properties[key]]),
  );
  const invalid = Object.entries(definition.properties)
    .some(([key, propertyDefinition]) => !validProperty(safeProperties[key], propertyDefinition));
  if (invalid) {
    console.warn(`Telemetry event ${eventType} was not queued because its properties do not match the approved schema.`);
    return;
  }
  if (eventType === 'page_viewed' && shouldThrottlePageView(safeProperties)) return;
  if (eventType === 'feature_clicked') {
    const key = `${safeProperties.featureName}:${safeProperties.pageContext}`;
    const now = Date.now();
    if (now - (featureClickTimes.get(key) ?? 0) < 500) return;
    featureClickTimes.set(key, now);
  }
  if (eventType === 'stock_validation_failed') {
    const existing = queue.find(event => event.event_type === eventType
      && event.properties.errorType === safeProperties.errorType
      && event.properties.productId === safeProperties.productId
      && event.properties.locationId === safeProperties.locationId);
    if (existing) {
      existing.properties.count = (existing.properties.count ?? 1) + 1;
      return;
    }
    safeProperties.count = 1;
  }

  queue.push({
    eventId: uuid(),
    timestamp: new Date().toISOString(),
    sessionId: currentSessionId,
    userId: currentUserId,
    event_type: eventType,
    schemaVersion: SCHEMA_VERSION,
    requestId,
    properties: safeProperties,
  });
  if (queue.length >= MAX_BATCH_SIZE) void flushQueue();
}
