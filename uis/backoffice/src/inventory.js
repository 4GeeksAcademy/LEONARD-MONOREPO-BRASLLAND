import '@fontsource/dm-sans/latin-400.css';
import '@fontsource/dm-sans/latin-500.css';
import '@fontsource/dm-sans/latin-600.css';
import '@fontsource/space-grotesk/latin-600.css';
import { requireSession } from './auth.js';
import { listIngredients, getIngredient, listOrders, registerOrder } from './inventory-api.js';
import { createIcons, Flame, MapPin, Package, ArrowDownToLine, ArrowUpFromLine, History, RefreshCw, Check } from 'lucide';

const icons = { Flame, MapPin, Package, ArrowDownToLine, ArrowUpFromLine, History, RefreshCw, Check };
const root = '/backoffice/inventory';
const routes = [
  ['products', 'Ingredients', 'package'],
  ['orders/inbound', 'Receive delivery', 'arrow-down-to-line'],
  ['orders/outbound', 'Log consumption / exit', 'arrow-up-from-line'],
  ['orders', 'Order history', 'history'],
];
const view = location.pathname.replace(`${root}/`, '').replace(/\/$/, '');
const active = routes.find(([route]) => route === view) ?? routes[0];
const categories = {
  carne: 'Meat', verduras_y_hortalizas: 'Vegetables', salsas_y_condimentos: 'Sauces & condiments',
  bebidas: 'Beverages', packaging: 'Packaging', productos_limpieza: 'Cleaning products',
  lacteos: 'Dairy', carbon_y_combustible: 'Charcoal & fuel',
};
const element = identifier => document.getElementById(identifier);
function node(tag, text, className) {
  const created = document.createElement(tag);
  if (text !== undefined) created.textContent = text;
  if (className) created.className = className;
  return created;
}
function message(identifier, text = '') {
  element(identifier).textContent = text;
  element(identifier).hidden = !text;
}
function drawIcons() { createIcons({ icons }); }

document.title = `${active[1]} | Brasaland Inventory`;
const tabs = element('inventory-tabs');
for (const [route, label, icon] of routes) {
  const link = node('a', undefined, 'inventory-tab');
  link.href = `${root}/${route}`;
  if (route === active[0]) link.setAttribute('aria-current', 'page');
  const image = node('i');
  image.dataset.lucide = icon;
  image.setAttribute('aria-hidden', 'true');
  link.append(image, node('span', label));
  tabs.append(link);
}
element('view-title').textContent = active[1];

if (await requireSession()) {
  const isProducts = active[0] === 'products';
  const isHistory = active[0] === 'orders';
  const outbound = active[0] === 'orders/outbound';
  const isForm = !isProducts && !isHistory;
  const locationSelect = element('location');
  const parameters = new URLSearchParams(location.search);
  const locations = [
    ...Array.from({ length: 10 }, (_, index) => `COL-${String(index + 1).padStart(2, '0')}`),
    ...Array.from({ length: 4 }, (_, index) => `FLA-${String(index + 1).padStart(2, '0')}`),
  ];
  for (const identifier of locations) {
    const option = node('option', `${identifier} / ${identifier.startsWith('COL') ? 'Colombia' : 'Florida'}`);
    option.value = identifier;
    locationSelect.append(option);
  }
  if (locations.includes(parameters.get('location_id'))) locationSelect.value = parameters.get('location_id');
  element('location-field').hidden = isHistory;
  element('inventory-table').hidden = isForm;
  element('order-form').hidden = !isForm;
  element('stock-status').hidden = !outbound;
  const form = element('order-form');
  const ingredientSelect = element('ingredient');
  const quantity = element('quantity');
  const submit = element('submit-order');
  element('submit-label').textContent = outbound ? 'Record consumption / exit' : 'Register delivery';
  let available = null;
  let stockUnit = '';
  let stockVersion = 0;
  let loadVersion = 0;
  let saving = false;

  function updateQuantity() {
    const exceeds = outbound && available !== null && Number(quantity.value) > available;
    message('quantity-warning', exceeds ? `Quantity exceeds the available stock of ${available} ${stockUnit}.` : '');
    quantity.setAttribute('aria-invalid', exceeds ? 'true' : 'false');
    submit.disabled = saving || !ingredientSelect.value || quantity.disabled || exceeds;
  }

  async function refreshStock() {
    const version = ++stockVersion;
    available = null;
    message('quantity-error');
    message('quantity-warning');
    quantity.disabled = outbound || !ingredientSelect.value;
    updateQuantity();
    if (!outbound || !ingredientSelect.value) {
      element('stock-status').textContent = 'Select an ingredient to see available stock.';
      return;
    }
    element('stock-status').textContent = 'Checking available stock...';
    try {
      const ingredient = await getIngredient(ingredientSelect.value, locationSelect.value);
      if (version !== stockVersion) return;
      available = ingredient.current_stock;
      stockUnit = ingredient.unit;
      element('stock-status').textContent = `Available at ${locationSelect.value}: ${available} ${stockUnit}`;
      quantity.disabled = false;
      updateQuantity();
    } catch (error) {
      if (version !== stockVersion) return;
      element('stock-status').textContent = 'Available stock could not be verified.';
      message('quantity-error', error.message);
    }
  }

  function renderTable(records) {
    const head = element('table-head');
    const rows = element('table-rows');
    head.replaceChildren();
    rows.replaceChildren();
    const headings = isProducts
      ? ['Ingredient', 'SKU', 'Category', 'Unit', 'Current stock', 'Stock level', 'Orders']
      : ['Ingredient', 'SKU', 'Location', 'Quantity', 'Order type', 'Created', 'Created by (user UUID)'];
    const headingRow = node('tr');
    for (const title of headings) {
      const heading = node('th', title);
      heading.scope = 'col';
      headingRow.append(heading);
    }
    head.append(headingRow);
    for (const record of records) {
      const row = node('tr');
      if (isProducts) {
        // Per restaurant and ingredient unit: <= 0 empty, <= 10 low, > 10 healthy.
        const level = record.current_stock <= 0 ? 'Out of stock' : record.current_stock <= 10 ? 'Low stock' : 'Healthy';
        const levelClass = record.current_stock <= 0 ? 'empty' : record.current_stock <= 10 ? 'low' : 'healthy';
        const badgeCell = node('td');
        badgeCell.append(node('span', level, `inventory-badge ${levelClass}`));
        const actions = node('td');
        const links = node('div', undefined, 'row-actions');
        for (const [direction, label, icon] of [
          ['inbound', 'Receive delivery', 'arrow-down-to-line'],
          ['outbound', 'Log consumption / exit', 'arrow-up-from-line'],
        ]) {
          const link = node('a', undefined, 'button secondary icon-button');
          link.title = `${label}: ${record.name}`;
          link.setAttribute('aria-label', link.title);
          link.href = `${root}/orders/${direction}?${new URLSearchParams({ ingredient_id: record.id, location_id: locationSelect.value })}`;
          const image = node('i');
          image.dataset.lucide = icon;
          image.setAttribute('aria-hidden', 'true');
          link.append(image);
          links.append(link);
        }
        actions.append(links);
        row.append(node('td', record.name), node('td', record.sku), node('td', categories[record.category] ?? record.category),
          node('td', record.unit), node('td', record.current_stock), badgeCell, actions);
      } else {
        const direction = node('td');
        direction.append(node('span', record.order_type === 'inbound' ? 'Inbound / delivery' : 'Outbound / consumption',
          `inventory-badge ${record.order_type === 'inbound' ? 'healthy' : 'exit'}`));
        const timestamp = node('time', new Date(record.created_at).toLocaleString());
        timestamp.dateTime = record.created_at;
        const dateCell = node('td');
        dateCell.append(timestamp);
        row.append(node('td', record.ingredient_name), node('td', record.ingredient_sku), node('td', record.location_id),
          node('td', record.quantity), direction, dateCell, node('td', record.user_uuid, 'user-uuid'));
      }
      rows.append(row);
    }
    element('table-caption').textContent = isProducts ? `Ingredient stock at ${locationSelect.value}` : 'Ingredient entries and exits across all locations';
    message('empty-state', records.length ? '' : isProducts ? 'No ingredients have been registered.' : 'No deliveries or consumption orders have been recorded.');
    drawIcons();
  }

  async function load() {
    const version = ++loadVersion;
    ++stockVersion;
    available = null;
    quantity.disabled = true;
    submit.disabled = true;
    ingredientSelect.disabled = true;
    message('page-error');
    message('quantity-error');
    message('quantity-warning');
    message('empty-state');
    element('table-rows').replaceChildren();
    message('page-status', 'Loading ingredient inventory...');
    if (outbound) element('stock-status').textContent = 'Checking available stock...';
    try {
      const records = await (isHistory ? listOrders() : listIngredients(locationSelect.value));
      if (version !== loadVersion) return;
      if (isForm) {
        const previous = ingredientSelect.value || parameters.get('ingredient_id');
        ingredientSelect.replaceChildren(new Option('Select an ingredient', ''));
        for (const ingredient of records) ingredientSelect.append(new Option(`${ingredient.name} / ${ingredient.unit}`, ingredient.id));
        if (records.some(ingredient => String(ingredient.id) === previous)) ingredientSelect.value = previous;
        ingredientSelect.disabled = false;
        message('empty-state', records.length ? '' : 'No ingredients have been registered.');
        await refreshStock();
      } else renderTable(records);
      if (version === loadVersion) message('page-status', isForm ? '' : `${records.length} ${isProducts ? 'ingredients' : 'orders'}`);
    } catch (error) {
      if (version !== loadVersion) return;
      message('page-status');
      message('page-error', error.message);
    }
  }

  ingredientSelect.addEventListener('change', () => {
    quantity.value = '';
    message('confirmation');
    refreshStock();
  });
  quantity.addEventListener('input', () => { message('quantity-error'); updateQuantity(); });
  locationSelect.addEventListener('change', () => { message('confirmation'); load(); });
  element('refresh').addEventListener('click', load);
  form.addEventListener('submit', async event => {
    event.preventDefault();
    if (submit.disabled || !form.reportValidity()) return;
    saving = true;
    updateQuantity();
    ingredientSelect.disabled = true;
    locationSelect.disabled = true;
    quantity.disabled = true;
    element('refresh').disabled = true;
    message('confirmation');
    message('page-error');
    message('quantity-error');
    try {
      await registerOrder(outbound ? 'outbound' : 'inbound', {
        ingredient_id: Number(ingredientSelect.value), location_id: locationSelect.value, quantity: quantity.value,
      });
      form.reset();
      message('confirmation', outbound ? 'Consumption / exit recorded successfully.' : 'Delivery registered successfully.');
      await refreshStock();
    } catch (error) {
      if (outbound && error.status === 400) {
        await refreshStock();
        message('quantity-error', error.message);
      } else message('page-error', error.message);
    } finally {
      saving = false;
      ingredientSelect.disabled = false;
      locationSelect.disabled = false;
      quantity.disabled = !ingredientSelect.value || (outbound && available === null);
      element('refresh').disabled = false;
      updateQuantity();
    }
  });
  drawIcons();
  await load();
}