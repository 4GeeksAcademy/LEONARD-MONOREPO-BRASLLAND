import { sessionFetch } from './auth.js';

export class InventoryError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

async function request(path, options = {}) {
  let response;
  try {
    response = await sessionFetch(`/api/backend/inventory${path}`, options);
  } catch (error) {
    if (error.status === 401) throw error;
    throw new InventoryError('Unable to reach ingredient inventory. Please try again.', 0);
  }
  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = payload?.detail ?? payload?.message;
    const message = typeof detail === 'string' ? detail : Array.isArray(detail)
      ? detail.map(issue => {
        const field = issue.field ?? (issue.loc ?? []).filter(part => part !== 'body').join(' ');
        return `${field ? `${field}: ` : ''}${issue.message ?? issue.msg ?? 'Invalid value'}`;
      }).join('; ')
      : `Ingredient inventory is unavailable (${response.status}). Please try again.`;
    throw new InventoryError(message, response.status);
  }
  if (payload === null) throw new InventoryError('Ingredient inventory returned an unreadable response. Please try again.', response.status);
  return payload;
}

export const listIngredients = location => request(`/products?${new URLSearchParams({ location_id: location })}`);
export const getIngredient = (identifier, location) => request(`/products/${encodeURIComponent(identifier)}?${new URLSearchParams({ location_id: location })}`);
export const listOrders = () => request('/orders');
export const registerOrder = (direction, payload) => request(`/orders/${direction}`, { method: 'POST', body: JSON.stringify(payload) });