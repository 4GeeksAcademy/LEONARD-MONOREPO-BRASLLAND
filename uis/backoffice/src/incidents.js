import '@fontsource/dm-sans/latin-400.css';
import '@fontsource/dm-sans/latin-500.css';
import '@fontsource/dm-sans/latin-600.css';
import '@fontsource/space-grotesk/latin-600.css';
import { requireSession, sessionFetch } from './auth.js';
import { createIcons, Flame, ChartNoAxesCombined, MapPin, ChevronRight, Truck, ClipboardList, RefreshCw, Check } from 'lucide';

if (await requireSession()) {
const icons = { Flame, ChartNoAxesCombined, MapPin, ChevronRight, Truck, ClipboardList, RefreshCw, Check };
const element = (id) => document.getElementById(id);
const statuses = [
  ['open', 'Open'], ['in_progress', 'In progress'], ['resolved', 'Resolved'], ['discarded', 'Discarded'],
];
const origins = [['customer', 'Customer'], ['branch', 'Branch'], ['internal', 'Internal']];
const categories = [
  ['CUSTOMER_COMPLAINT', 'Customer complaint'], ['EQUIPMENT', 'Equipment'], ['SUPPLY', 'Supply'],
  ['FOOD_QUALITY', 'Food quality'], ['STAFF', 'Staff'],
];
const branches = [
  'central', ...Array.from({ length: 10 }, (_, index) => `COL-${String(index + 1).padStart(2, '0')}`),
  ...Array.from({ length: 4 }, (_, index) => `FLA-${String(index + 1).padStart(2, '0')}`),
];
const transitions = {
  open: ['in_progress', 'discarded'],
  in_progress: ['resolved', 'discarded'],
  resolved: ['in_progress', 'discarded'],
  discarded: [],
};
const form = element('incident-form');
let records = [];
let busy = false;

class RequestFailure extends Error {
  constructor(message, fields = {}) {
    super(message);
    this.fields = fields;
  }
}

async function api(path, options = {}) {
  let response;
  try {
    response = await sessionFetch(path, options);
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') throw error;
    throw new RequestFailure('The incident service is unavailable. Please try again.');
  }
  let body = {};
  try {
    body = await response.json();
  } catch {
    if (response.ok) throw new RequestFailure('The incident service returned an unreadable response. Please try again.');
  }
  if (!response.ok) {
    const fields = {};
    if (response.status === 422 && Array.isArray(body.detail)) {
      for (const issue of body.detail) if (issue.field) fields[issue.field.split('.')[0]] = true;
      throw new RequestFailure('Please review the highlighted fields.', fields);
    }
    if (response.status === 400) throw new RequestFailure('That status change is not allowed. The incident was restored.');
    if (response.status === 404) throw new RequestFailure('This incident is no longer available. Refresh the list.');
    throw new RequestFailure('The request could not be completed. Please try again.');
  }
  return body;
}

function node(tag, text, className) {
  const created = document.createElement(tag);
  if (text !== undefined) created.textContent = text;
  if (className) created.className = className;
  return created;
}

function toggleError(id, message = '') {
  const target = element(id);
  target.textContent = message;
  target.hidden = !message;
}

function clearFieldErrors() {
  for (const field of ['title', 'description', 'category', 'status', 'origin', 'branch']) {
    const input = element(field);
    input.removeAttribute('aria-invalid');
    const error = element(`${field}-error`);
    error.textContent = '';
    error.hidden = true;
  }
}

function showFieldErrors(fields) {
  const messages = {
    title: 'Enter a short incident title.', description: 'Add at least five characters.',
    category: 'Choose one of the listed categories.', status: 'Choose a valid status.',
    origin: 'Choose a valid origin.', branch: 'Choose a branch or Central.',
  };
  let shown = false;
  for (const field of Object.keys(messages)) {
    if (!fields[field]) continue;
    element(field).setAttribute('aria-invalid', 'true');
    const error = element(`${field}-error`);
    error.textContent = messages[field];
    error.hidden = false;
    shown = true;
  }
  return shown;
}

function validateForm() {
  clearFieldErrors();
  const values = new FormData(form);
  const errors = {};
  for (const field of ['title', 'description', 'category', 'status', 'origin', 'branch']) {
    if (!String(values.get(field) || '').trim()) errors[field] = true;
  }
  if (String(values.get('title') || '').trim().length > 160) errors.title = true;
  if (String(values.get('description') || '').trim().length < 5) errors.description = true;
  if (showFieldErrors(errors)) {
    element(Object.keys(errors)[0]).focus();
    return false;
  }
  return true;
}

function setBusy(value) {
  busy = value;
  for (const control of form.elements) control.disabled = value;
  element('submit-progress').hidden = !value;
  element('submit-incident').querySelector('span').textContent = value ? 'Saving...' : 'Register incident';
}

function branchLabel(branch) {
  return branch === 'central' ? 'Central' : branch;
}

function setBranchHighlight() {
  element('branch-field').classList.toggle('is-highlighted', element('origin').value === 'branch');
}

async function submitIncident(event) {
  event.preventDefault();
  if (busy) return;
  toggleError('form-error');
  element('form-success').hidden = true;
  if (!validateForm()) return;
  setBusy(true);
  try {
    const values = Object.fromEntries(new FormData(form));
    await api('/api/incidents', { method: 'POST', body: JSON.stringify(values) });
    form.reset();
    clearFieldErrors();
    setBranchHighlight();
    element('form-success').textContent = 'Incident registered successfully.';
    element('form-success').hidden = false;
    await Promise.all([loadIncidents(), loadSummary()]);
  } catch (error) {
    const hasFields = showFieldErrors(error.fields || {});
    toggleError('form-error', hasFields ? 'Please correct the highlighted fields.'
      : error instanceof RequestFailure ? error.message : 'The incident could not be registered. Please review the form and try again.');
  } finally {
    setBusy(false);
  }
}

function renderSummary(summary) {
  const groups = [
    ['Status', 'by_status', statuses], ['Category', 'by_category', categories],
    ['Origin', 'by_origin', origins], ['Branch', 'by_branch', branches.map((branch) => [branch, branchLabel(branch)])],
  ];
  const container = element('summary-groups');
  container.replaceChildren();
  for (const [title, key, options] of groups) {
    const section = node('section', undefined, 'summary-group');
    section.append(node('h3', title));
    const definitionList = node('dl');
    for (const [value, label] of options) {
      const item = node('div');
      item.append(node('dt', label), node('dd', String(summary[key]?.[value] ?? 0)));
      definitionList.append(item);
    }
    section.append(definitionList);
    container.append(section);
  }
  element('summary-message').textContent = `${summary.total} total incidents`;
  container.hidden = false;
}

async function loadSummary() {
  element('summary-message').textContent = 'Loading metrics...';
  element('summary-groups').hidden = true;
  element('retry-summary').hidden = true;
  try {
    renderSummary(await api('/api/incidents/summary'));
  } catch {
    element('summary-message').textContent = 'Summary is temporarily unavailable.';
    element('retry-summary').hidden = false;
  }
}

function statusSelect(record) {
  const select = node('select', undefined, 'incident-status');
  select.setAttribute('aria-label', `Update status for ${record.title}`);
  for (const [value, label] of statuses) {
    if (value !== record.status && !transitions[record.status].includes(value)) continue;
    const option = node('option', label);
    option.value = value;
    select.append(option);
  }
  select.value = record.status;
  select.addEventListener('change', () => updateStatus(record, select));
  return select;
}

async function updateStatus(record, select) {
  const requested = select.value;
  select.disabled = true;
  toggleError('list-error');
  try {
    await api(`/api/incidents/${record.id}/status`, {
      method: 'PATCH', body: JSON.stringify({ status: requested }),
    });
    await Promise.all([loadIncidents(), loadSummary()]);
  } catch (error) {
    toggleError('list-error', error instanceof RequestFailure ? error.message : 'The incident status could not be updated. Refresh the list and try again.');
    renderList();
  }
}

function renderList() {
  const rows = element('incident-rows');
  rows.replaceChildren();
  element('list-count').textContent = `${records.length} ${records.length === 1 ? 'incident' : 'incidents'}`;
  element('empty-incidents').hidden = records.length !== 0;
  element('incident-table-wrap').hidden = records.length === 0;
  element('list-message').hidden = true;
  for (const record of records) {
    const row = node('tr');
    const incident = node('td');
    incident.append(node('strong', record.title, 'incident-title'));
    incident.append(node('span', record.description, 'incident-description'));
    row.append(incident);
    row.append(node('td', categories.find(([value]) => value === record.category)?.[1] || record.category));
    row.append(node('td', origins.find(([value]) => value === record.origin)?.[1] || record.origin));
    row.append(node('td', branchLabel(record.branch)));
    const created = new Date(record.created_at);
    row.append(node('td', Number.isNaN(created.getTime()) ? 'Unknown' : new Intl.DateTimeFormat('en', { dateStyle: 'medium' }).format(created)));
    const statusCell = node('td');
    statusCell.append(statusSelect(record));
    row.append(statusCell);
    rows.append(row);
  }
}

async function loadIncidents() {
  element('list-message').textContent = 'Loading incidents...';
  element('list-message').hidden = false;
  element('incident-table-wrap').hidden = true;
  element('empty-incidents').hidden = true;
  element('retry-list').hidden = true;
  toggleError('list-error');
  const parameters = new URLSearchParams();
  for (const key of ['status', 'origin', 'branch']) {
    const value = element(`${key}-filter`).value;
    if (value) parameters.set(key, value);
  }
  try {
    records = await api(`/api/incidents?${parameters}`);
    renderList();
  } catch (error) {
    records = [];
    element('list-message').textContent = 'The incident list could not be loaded.';
    toggleError('list-error', error instanceof RequestFailure ? error.message : 'Refresh the list to try again.');
    element('retry-list').hidden = false;
  }
}

for (const branch of branches.slice(1)) {
  const option = node('option', branch);
  option.value = branch;
  element('branch').append(option);
  element('branch-filter').append(option.cloneNode(true));
}
element('branch-filter').insertBefore(new Option('Central', 'central'), element('branch-filter').options[1]);
element('origin').addEventListener('change', setBranchHighlight);
form.addEventListener('submit', submitIncident);
for (const filter of ['status', 'origin', 'branch']) element(`${filter}-filter`).addEventListener('change', loadIncidents);
element('retry-list').addEventListener('click', loadIncidents);
element('retry-summary').addEventListener('click', loadSummary);
element('refresh-all').addEventListener('click', () => { loadIncidents(); loadSummary(); });

createIcons({ icons });
setBranchHighlight();
loadIncidents();
loadSummary();
}