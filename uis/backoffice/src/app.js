import '@fontsource/dm-sans/latin-400.css';
import '@fontsource/dm-sans/latin-500.css';
import '@fontsource/dm-sans/latin-600.css';
import '@fontsource/space-grotesk/latin-600.css';
import { requireSession, sessionFetch } from './auth.js';
import {
  createIcons, Flame, ChartNoAxesCombined, MapPin, ChevronRight, Download,
  FileSpreadsheet, FolderOpen, ShieldCheck, ArrowRight, ChartColumn, TriangleAlert, CircleCheck, Truck,
} from 'lucide';

if (await requireSession()) {
createIcons({ icons: { Flame, ChartNoAxesCombined, MapPin, ChevronRight, Download,
  FileSpreadsheet, FolderOpen, ShieldCheck, ArrowRight, ChartColumn, TriangleAlert, CircleCheck, Truck } });

const element = (identifier) => document.getElementById(identifier);
const input = element('file-input');
const form = element('upload-form');
const dropZone = element('drop-zone');
const analyzeButton = element('analyze');
const downloadButton = element('download');
const categoryNames = {
  CUSTOMER_COMPLAINT: 'Customer complaint', EQUIPMENT: 'Equipment',
  SUPPLY: 'Supply', FOOD_QUALITY: 'Food quality', STAFF: 'Staff',
};
const scoreNames = ['Very dissatisfied', 'Dissatisfied', 'Neutral', 'Satisfied', 'Very satisfied'];
let selectedFile = null;
let busy = false;
let hasResults = false;

function showError(message) {
  element('error').textContent = message;
  element('error').hidden = !message;
}

function setBusy(value, message = '') {
  busy = value;
  form.classList.toggle('busy', value);
  form.setAttribute('aria-busy', String(value));
  input.disabled = value;
  analyzeButton.disabled = value || !selectedFile;
  downloadButton.disabled = value || !hasResults;
  analyzeButton.querySelector('span').textContent = value ? 'Analyzing...' : 'Analyze file';
  element('progress').textContent = message;
  element('progress').hidden = !message;
}

function chooseFile(file) {
  if (busy || !file) return;
  showError('');
  selectedFile = null;
  analyzeButton.disabled = true;
  element('file-name').textContent = 'Incident CSV';
  element('file-detail').textContent = 'No file selected';
  if (!file.name.toLowerCase().endsWith('.csv')) {
    showError('Select a .csv file encoded as UTF-8.');
    return;
  }
  if (file.size === 0 || file.size > 256 * 1024 * 1024 - 4096) {
    showError(file.size === 0 ? 'The CSV file is empty.' : 'Upload exceeds the 256 MiB limit.');
    return;
  }
  selectedFile = file;
  element('file-name').textContent = file.name;
  element('file-detail').textContent = file.size < 1024 * 1024
    ? `${(file.size / 1024).toFixed(1)} KB` : `${(file.size / (1024 * 1024)).toFixed(1)} MB`;
  analyzeButton.disabled = false;
}

input.addEventListener('change', () => chooseFile(input.files[0]));
for (const eventName of ['dragenter', 'dragover']) {
  dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    if (!busy) dropZone.classList.add('dragging');
  });
}
for (const eventName of ['dragleave', 'drop']) {
  dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropZone.classList.remove('dragging');
  });
}
dropZone.addEventListener('drop', (event) => {
  if (event.dataTransfer.files.length > 1) {
    showError('Select one CSV file at a time.');
    return;
  }
  chooseFile(event.dataTransfer.files[0]);
});
document.addEventListener('dragover', (event) => event.preventDefault());
document.addEventListener('drop', (event) => event.preventDefault());

function cell(text, className = '') {
  const node = document.createElement('td');
  node.textContent = text;
  node.className = className;
  return node;
}

function formatCount(count) {
  return count.toLocaleString('en-US');
}

function renderSummary(summary) {
  const percentage = (count) => summary.valid_records ? count / summary.valid_records * 100 : 0;
  element('empty-state').hidden = true;
  element('results').hidden = false;
  element('analysis-time').textContent = new Intl.DateTimeFormat('en', {
    dateStyle: 'medium', timeStyle: 'short',
  }).format(new Date());
  element('total-records').textContent = formatCount(summary.total_records);
  element('valid-records').textContent = formatCount(summary.valid_records);
  element('invalid-records').textContent = formatCount(summary.invalid_records);
  element('closed-records').textContent = formatCount(summary.statuses.CLOSED);
  element('valid-percentage').textContent = `${(summary.valid_records / summary.total_records * 100).toFixed(1)}% of source records`;
  element('scored-cases').textContent = `${formatCount(summary.satisfaction.scored_cases)} scored cases`;
  const invalid = summary.invalid_records > 0;
  element('validation').classList.toggle('clean', !invalid);
  element('warning-icon').toggleAttribute('hidden', !invalid);
  element('clean-icon').toggleAttribute('hidden', invalid);
  element('validation-title').textContent = invalid ? 'Invalid records detected' : 'Validation complete';
  element('validation-message').textContent = invalid
    ? `${formatCount(summary.invalid_records)} invalid ${summary.invalid_records === 1 ? 'record' : 'records'} excluded from analysis.`
    : 'No invalid records.';
  element('invalid-table').hidden = !invalid;
  element('overlap-note').hidden = !invalid;
  const invalidRows = element('invalid-rows');
  invalidRows.replaceChildren();
  for (const [rule, count] of Object.entries(summary.invalid_breakdown)) {
    if (!count) continue;
    const row = document.createElement('tr');
    row.append(cell(summary.rule_labels[rule] || rule), cell(formatCount(count)));
    invalidRows.append(row);
  }
  const categoryRows = element('category-rows');
  categoryRows.replaceChildren();
  for (const [category, count] of Object.entries(summary.categories)) {
    const row = document.createElement('tr');
    const name = cell(categoryNames[category] || category, 'category-cell');
    name.title = category;
    const track = document.createElement('div');
    track.className = 'category-track';
    const fill = document.createElement('span');
    fill.className = 'category-fill';
    fill.style.width = `${percentage(count)}%`;
    track.append(fill);
    name.append(track);
    row.append(name, cell(formatCount(count)), cell(`${percentage(count).toFixed(1)}%`));
    categoryRows.append(row);
  }
  const statusRows = element('status-rows');
  const statusBar = element('status-bar');
  statusRows.replaceChildren();
  statusBar.replaceChildren();
  for (const [status, count] of Object.entries(summary.statuses)) {
    const row = document.createElement('tr');
    const name = cell('');
    const label = document.createElement('span');
    label.className = 'status-label';
    const dot = document.createElement('span');
    dot.className = `status-dot status-${status.toLowerCase()}`;
    label.append(dot, document.createTextNode(status));
    name.append(label);
    row.append(name, cell(formatCount(count)), cell(`${percentage(count).toFixed(1)}%`));
    statusRows.append(row);
    const segment = document.createElement('span');
    segment.className = `status-${status.toLowerCase()}`;
    segment.style.width = `${percentage(count)}%`;
    statusBar.append(segment);
  }
  const satisfaction = summary.satisfaction;
  element('average-score').textContent = satisfaction.average === null ? 'N/A' : satisfaction.average.toFixed(2);
  element('satisfaction-count').textContent = `${formatCount(satisfaction.scored_cases)} of ${formatCount(satisfaction.closed_cases)} closed cases scored`;
  const chart = element('score-chart');
  chart.replaceChildren();
  const maximum = Math.max(...Object.values(satisfaction.scores), 1);
  for (const [score, count] of Object.entries(satisfaction.scores)) {
    const column = document.createElement('div');
    column.className = 'score-column';
    column.title = `Score ${score}: ${scoreNames[Number(score) - 1]} (${count} cases)`;
    column.setAttribute('aria-label', column.title);
    const number = document.createElement('strong');
    number.textContent = formatCount(count);
    const track = document.createElement('div');
    track.className = 'score-track';
    const bar = document.createElement('div');
    bar.className = 'score-bar';
    bar.style.height = `${count / maximum * 100}%`;
    track.append(bar);
    const label = document.createElement('span');
    label.textContent = `Score ${score}`;
    column.append(number, track, label);
    chart.append(column);
  }
  hasResults = true;
}

async function errorMessage(response) {
  try {
    const body = await response.json();
    return typeof body.detail === 'string' ? body.detail : `Request failed (${response.status}).`;
  } catch {
    return `Request failed (${response.status}).`;
  }
}

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  if (!selectedFile || busy) return;
  showError('');
  setBusy(true, 'Analyzing incident records...');
  const payload = new FormData();
  payload.append('file', selectedFile);
  try {
    const response = await sessionFetch('/api/incidents/analyze', { method: 'POST', body: payload });
    if (!response.ok) throw new Error(await errorMessage(response));
    renderSummary(await response.json());
    element('progress').textContent = 'Analysis complete.';
  } catch (error) {
    showError(error.message === 'Failed to fetch' ? 'Cannot reach the analysis service. Please try again.' : error.message);
  } finally {
    setBusy(false);
  }
});

downloadButton.addEventListener('click', async () => {
  if (busy || !hasResults) return;
  showError('');
  downloadButton.disabled = true;
  try {
    const response = await sessionFetch('/api/incidents/results/export');
    if (!response.ok) throw new Error(await errorMessage(response));
    const url = URL.createObjectURL(await response.blob());
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = 'results.csv';
    document.body.append(anchor);
    anchor.click();
    anchor.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  } catch (error) {
    showError(error.message === 'Failed to fetch' ? 'Cannot reach the export service. Please try again.' : error.message);
  } finally {
    downloadButton.disabled = false;
  }
});
}