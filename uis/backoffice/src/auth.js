import { apiRequest, endSession, getToken, TOKEN_KEY } from '../../../packages/shared/auth/session.ts';

export { sessionFetch } from '../../../packages/shared/auth/session.ts';

export async function requireSession() {
  if (!getToken()) {
    endSession();
    return false;
  }
  try {
    await apiRequest('/api/backend/auth/me');
    document.body.hidden = false;
    document.getElementById('logout').addEventListener('click', endSession);
    window.addEventListener('storage', event => {
      if ((event.key === TOKEN_KEY || event.key === null) && !getToken()) endSession();
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