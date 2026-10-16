import '@fontsource/dm-sans/latin-400.css';
import '@fontsource/dm-sans/latin-500.css';
import '@fontsource/dm-sans/latin-600.css';
import '@fontsource/space-grotesk/latin-600.css';
import { requireSession, sessionFetch } from './auth.js';
import { createIcons, Flame, ChartNoAxesCombined, MapPin, ChevronRight, Truck, Plus, X, Check, Save, Pause, Play, RefreshCw } from 'lucide';

if (await requireSession()) {
const icons = { Flame, ChartNoAxesCombined, MapPin, ChevronRight, Truck, Plus, X, Check, Save, Pause, Play, RefreshCw };
const element = (identifier) => document.getElementById(identifier);
const categories = {
  carne: 'Meat', verduras_y_hortalizas: 'Vegetables', salsas_y_condimentos: 'Sauces & condiments',
  bebidas: 'Beverages', packaging: 'Packaging', productos_limpieza: 'Cleaning products',
  lacteos: 'Dairy', carbon_y_combustible: 'Charcoal & fuel',
};
const form = element('supplier-form');
const dialog = element('supplier-dialog');
let records = [];
let currentLoad;

function showError(identifier, message = '') {
  element(identifier).textContent = message;
  element(identifier).hidden = !message;
}

async function api(url, options = {}) {
  let response;
  try {
    response = await sessionFetch(url, options);
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') throw error;
    throw new Error('The supplier service is unavailable. Please try again.');
  }
  if (!response.ok) {
    if (response.status === 404) throw new Error('That supplier is no longer available. Refresh the directory and try again.');
    if (response.status === 422) throw new Error('Please review the supplier information and try again.');
    throw new Error('The request could not be completed. Please try again.');
  }
  try {
    return await response.json();
  } catch {
    throw new Error('The supplier service returned an unreadable response. Please try again.');
  }
}

function node(tag, text, className) {
  const created = document.createElement(tag);
  if (text !== undefined) created.textContent = text;
  if (className) created.className = className;
  return created;
}

function iconButton(icon, label, className = 'button secondary icon-button') {
  const button = node('button', undefined, className);
  button.title = label;
  button.setAttribute('aria-label', label);
  const image = node('i');
  image.dataset.lucide = icon;
  image.setAttribute('aria-hidden', 'true');
  button.append(image);
  return button;
}

function render() {
  const status = element('status-filter').value;
  const visible = records.filter((record) => !status || record.status === status);
  element('supplier-rows').replaceChildren();
  element('directory-message').textContent = `${visible.length} suppliers / ${visible.filter((record) => record.status === 'active').length} active`;
  element('no-suppliers').hidden = visible.length !== 0;
  for (const record of visible) {
    const row = node('tr');
    row.dataset.id = record.id;
    const supplier = node('td');
    supplier.append(node('strong', record.name));
    if (record.contact_email) supplier.append(node('small', record.contact_email));
    if (record.notes) {
      const details = node('details');
      details.append(node('summary', 'Notes'), node('p', record.notes));
      supplier.append(details);
    }
    const categoryCell = node('td');
    for (const category of record.categories) categoryCell.append(node('span', categories[category], 'category-label'));
    const rateCell = node('td');
    const rateForm = node('form', undefined, 'rate-form');
    const rate = node('input');
    rate.type = 'number';
    rate.min = '0.000001';
    rate.step = 'any';
    rate.required = true;
    rate.value = record.rate_per_unit;
    rate.setAttribute('aria-label', `Rate for ${record.name}`);
    const save = iconButton('save', `Save rate for ${record.name}`);
    save.type = 'submit';
    rateForm.append(rate, node('span', record.currency, 'currency-label'), save);
    rateForm.addEventListener('submit', async (event) => {
      event.preventDefault();
      await update(record, 'rate', { rate_per_unit: Number(rate.value) }, save);
    });
    const timestamp = node('small', new Date(record.updated_at).toLocaleString());
    timestamp.title = `Last rate update: ${record.updated_at}`;
    rateCell.append(rateForm, timestamp);
    const statusCell = node('td');
    statusCell.append(node('span', record.status === 'active' ? 'Active' : 'Suspended', `status-badge ${record.status}`));
    const action = record.status === 'active' ? 'Suspend' : 'Activate';
    const toggle = iconButton(record.status === 'active' ? 'pause' : 'play', `${action} ${record.name}`, 'status-button');
    toggle.append(node('span', action));
    toggle.addEventListener('click', () => update(record, 'status', { status: record.status === 'active' ? 'suspended' : 'active' }, toggle));
    statusCell.append(toggle);
    row.append(supplier, node('td', record.country), categoryCell, rateCell, statusCell);
    element('supplier-rows').append(row);
  }
  createIcons({ icons });
}

async function update(record, field, payload, control) {
  control.disabled = true;
  element('directory-message').textContent = `Saving changes to ${record.name}...`;
  showError('directory-error');
  try {
    const updated = await api(`/suppliers/${record.id}/${field}`, { method: 'PATCH', body: JSON.stringify(payload) });
    records = records.map((existing) => existing.id === updated.id ? updated : existing);
    render();
  } catch {
    showError('directory-error', 'The supplier could not be updated. Please try again.');
    element('directory-message').textContent = 'Supplier directory is ready.';
  } finally {
    control.disabled = false;
  }
}

async function load() {
  currentLoad?.abort();
  const controller = new AbortController();
  currentLoad = controller;
  showError('directory-error');
  element('directory-message').textContent = 'Loading suppliers...';
  const parameters = new URLSearchParams();
  for (const key of ['country', 'category']) {
    if (element(`${key}-filter`).value) parameters.set(key, element(`${key}-filter`).value);
  }
  try {
    records = await api(`/suppliers?${parameters}`, { signal: controller.signal });
    render();
  } catch (error) {
    if (!(error instanceof Error && error.name === 'AbortError')) {
      records = [];
      element('supplier-rows').replaceChildren();
      element('no-suppliers').hidden = true;
      element('directory-message').textContent = 'Directory unavailable';
      showError('directory-error', 'The supplier directory could not be loaded. Select Refresh to try again.');
    }
  } finally {
    if (currentLoad === controller) currentLoad = undefined;
  }
}

for (const [value, label] of Object.entries(categories)) {
  const option = node('option', label);
  option.value = value;
  element('category-filter').append(option);
  const checkbox = node('input');
  checkbox.type = 'checkbox';
  checkbox.name = 'categories';
  checkbox.value = value;
  const categoryLabel = node('label');
  categoryLabel.append(checkbox, node('span', label));
  element('category-options').append(categoryLabel);
}

function validateCategories() {
  const first = form.querySelector('[name="categories"]');
  first.setCustomValidity(form.querySelector('[name="categories"]:checked') ? '' : 'Select at least one category.');
}
element('category-options').addEventListener('change', validateCategories);
for (const key of ['country', 'category']) element(`${key}-filter`).addEventListener('change', load);
element('status-filter').addEventListener('change', render);
element('refresh').addEventListener('click', load);
element('new-supplier').addEventListener('click', () => { showError('form-error'); validateCategories(); dialog.showModal(); });
element('close-dialog').addEventListener('click', () => dialog.close());
form.elements.country.addEventListener('change', () => { form.elements.currency.value = form.elements.country.value === 'Colombia' ? 'COP' : 'USD'; });
form.addEventListener('submit', async (event) => {
  event.preventDefault();
  const submit = form.querySelector('[type="submit"]');
  const submitLabel = submit.querySelector('span');
  submit.disabled = true;
  if (submitLabel) submitLabel.textContent = 'Saving...';
  showError('form-error');
  const values = new FormData(form);
  const payload = Object.fromEntries(values);
  payload.categories = values.getAll('categories');
  payload.rate_per_unit = Number(payload.rate_per_unit);
  payload.contact_email = payload.contact_email || null;
  payload.notes = payload.notes || null;
  try {
    await api('/suppliers', { method: 'POST', body: JSON.stringify(payload) });
    dialog.close();
    form.reset();
    validateCategories();
    await load();
  } catch {
    showError('form-error', 'The supplier could not be registered. Review the form and try again.');
  } finally {
    submit.disabled = false;
      if (submitLabel) submitLabel.textContent = 'Register supplier';
  }
});

createIcons({ icons });
load();
}