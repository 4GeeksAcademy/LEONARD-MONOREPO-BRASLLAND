import { requireSession, sessionFetch } from './auth.js';
import { createIcons, RefreshCw, X, Activity, ChevronRight, Flame, MapPin } from 'lucide';

if (await requireSession()) {
  createIcons({ icons: { RefreshCw, X, Activity, ChevronRight, Flame, MapPin } });

  const element = (id) => document.getElementById(id);
  const startDateInput = element('start-date');
  const endDateInput = element('end-date');
  const refreshButton = element('refresh');
  const resetButton = element('reset');
  const errorElement = element('error');
  const loadingElement = element('loading');
  const metricsContainer = element('metrics-container');
  const emptyState = element('empty-state');
  const reportPeriod = element('report-period');

  function showError(message) {
    errorElement.textContent = message;
    errorElement.hidden = !message;
  }

  function setLoading(loading) {
    loadingElement.hidden = !loading;
  }

  function formatDate(date) {
    return date.toISOString().split('T')[0];
  }

  function getDefaultDates() {
    const end = new Date();
    const start = new Date();
    start.setDate(start.getDate() - 7);
    return { start, end };
  }

  function setDateInputs(start, end) {
    startDateInput.value = formatDate(start);
    endDateInput.value = formatDate(end);
  }

  function renderSimpleBarChart(container, data, labelKey, valueKey) {
    """Render a simple text-based bar chart."""
    if (!data || data.length === 0) {
      container.innerHTML = '<p style="text-align: center; color: #999;">No data available</p>';
      return;
    }

    const maxValue = Math.max(...data.map(d => d[valueKey]));
    const barWidth = 200;
    
    let html = '<div style="font-family: monospace; font-size: 0.85rem;">';
    data.forEach(item => {
      const pct = (item[valueKey] / maxValue) * 100;
      const barLength = Math.round((pct / 100) * barWidth);
      const bar = '█'.repeat(Math.max(1, barLength));
      html += `<div style="margin-bottom: 0.5rem;">
        <div>${item[labelKey]}</div>
        <div>${bar} ${item[valueKey]}</div>
      </div>`;
    });
    html += '</div>';
    
    container.innerHTML = html;
  }

  function renderPercentageChart(container, data, labelKey, percentKey) {
    """Render percentage-based chart."""
    if (!data || data.length === 0) {
      container.innerHTML = '<p style="text-align: center; color: #999;">No data available</p>';
      return;
    }

    let html = '<div style="font-family: monospace; font-size: 0.85rem;">';
    data.forEach(item => {
      const pct = Math.round(item[percentKey] * 100);
      const filled = Math.round(pct / 5);
      const empty = 20 - filled;
      const bar = '█'.repeat(filled) + '░'.repeat(empty);
      html += `<div style="margin-bottom: 0.5rem;">
        <div>${item[labelKey]}</div>
        <div>${bar} ${pct}%</div>
      </div>`;
    });
    html += '</div>';
    
    container.innerHTML = html;
  }

  async function fetchReport(startDate, endDate) {
    showError('');
    setLoading(true);
    metricsContainer.hidden = true;
    emptyState.hidden = true;
    reportPeriod.hidden = true;

    try {
      const params = new URLSearchParams({
        start_date: startDate.toISOString(),
        end_date: endDate.toISOString(),
      });
      
      const response = await sessionFetch(`/telemetry/report?${params}`);
      if (!response.ok) {
        throw new Error(`Failed to fetch telemetry report: ${response.statusText}`);
      }

      const data = await response.json();
      renderReport(data);
      reportPeriod.hidden = false;
      metricsContainer.hidden = false;
    } catch (error) {
      console.error('Error fetching telemetry report:', error);
      showError(`Failed to load telemetry data: ${error.message}`);
      emptyState.hidden = false;
    } finally {
      setLoading(false);
    }
  }

  function renderReport(data) {
    const { period, metrics } = data;
    
    // Update period display
    const periodText = element('period-text');
    const startDate = new Date(period.from);
    const endDate = new Date(period.to);
    periodText.textContent = `Report period: ${formatDate(startDate)} to ${formatDate(endDate)}`;

    // Render events by type and day
    renderEventsTable(metrics.events_per_day || []);
    renderSimpleBarChart(
      element('events-chart'),
      metrics.events_per_day || [],
      'event_type',
      'count'
    );
    
    // Render error rate by type
    renderErrorRateTable(metrics.error_rate_by_type || []);
    renderPercentageChart(
      element('errors-chart'),
      metrics.error_rate_by_type || [],
      'event_type',
      'error_rate'
    );
    
    // Render API latency by day
    renderLatencyTable(metrics.api_latency_by_day || []);
    renderSimpleBarChart(
      element('latency-chart'),
      metrics.api_latency_by_day || [],
      'date',
      'avg_latency_ms'
    );
    
    // Render authentication failure rate
    renderAuthFailureTable(metrics.auth_failure_rate || []);
    renderPercentageChart(
      element('auth-chart'),
      metrics.auth_failure_rate || [],
      'date',
      'failure_rate'
    );
  }

  function renderEventsTable(events) {
    const tbody = element('events-table').querySelector('tbody');
    tbody.innerHTML = '';

    if (events.length === 0) {
      tbody.innerHTML = '<tr><td colspan="3" style="text-align: center; color: #999;">No data available</td></tr>';
      return;
    }

    events.forEach((row) => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>${row.date}</td>
        <td>${row.event_type}</td>
        <td style="text-align: right;">${row.count}</td>
      `;
      tbody.appendChild(tr);
    });
  }

  function renderErrorRateTable(errors) {
    const tbody = element('errors-table').querySelector('tbody');
    tbody.innerHTML = '';

    if (errors.length === 0) {
      tbody.innerHTML = '<tr><td colspan="4" style="text-align: center; color: #999;">No data available</td></tr>';
      return;
    }

    errors.forEach((row) => {
      const tr = document.createElement('tr');
      const errorPercentage = (row.error_rate * 100).toFixed(2);
      tr.innerHTML = `
        <td>${row.event_type}</td>
        <td style="text-align: right;">${row.error_count}</td>
        <td style="text-align: right;">${row.total_count}</td>
        <td style="text-align: right;"><strong>${errorPercentage}%</strong></td>
      `;
      tbody.appendChild(tr);
    });
  }

  function renderLatencyTable(latencies) {
    const tbody = element('latency-table').querySelector('tbody');
    tbody.innerHTML = '';

    if (latencies.length === 0) {
      tbody.innerHTML = '<tr><td colspan="4" style="text-align: center; color: #999;">No data available</td></tr>';
      return;
    }

    latencies.forEach((row) => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>${row.date}</td>
        <td style="text-align: right;">${row.avg_latency_ms}ms</td>
        <td style="text-align: right;">${row.min_latency_ms}ms</td>
        <td style="text-align: right;">${row.max_latency_ms}ms</td>
      `;
      tbody.appendChild(tr);
    });
  }

  function renderAuthFailureTable(authData) {
    const tbody = element('auth-table').querySelector('tbody');
    tbody.innerHTML = '';

    if (authData.length === 0) {
      tbody.innerHTML = '<tr><td colspan="4" style="text-align: center; color: #999;">No data available</td></tr>';
      return;
    }

    authData.forEach((row) => {
      const tr = document.createElement('tr');
      const failurePercentage = (row.failure_rate * 100).toFixed(2);
      tr.innerHTML = `
        <td>${row.date}</td>
        <td style="text-align: right;">${row.login_failed}</td>
        <td style="text-align: right;">${row.login_succeeded}</td>
        <td style="text-align: right;"><strong>${failurePercentage}%</strong></td>
      `;
      tbody.appendChild(tr);
    });
  }

  // Initialize with default 7-day period
  const { start, end } = getDefaultDates();
  setDateInputs(start, end);
  await fetchReport(start, end);

  // Event listeners
  refreshButton.addEventListener('click', () => {
    const start = new Date(startDateInput.value);
    const end = new Date(endDateInput.value);
    end.setDate(end.getDate() + 1); // Exclusive end date
    fetchReport(start, end);
  });

  resetButton.addEventListener('click', () => {
    const { start, end } = getDefaultDates();
    setDateInputs(start, end);
    fetchReport(start, end);
  });

  // Auto-refresh on date input change
  startDateInput.addEventListener('change', () => {
    const start = new Date(startDateInput.value);
    const end = new Date(endDateInput.value);
    end.setDate(end.getDate() + 1); // Exclusive end date
    fetchReport(start, end);
  });

  endDateInput.addEventListener('change', () => {
    const start = new Date(startDateInput.value);
    const end = new Date(endDateInput.value);
    end.setDate(end.getDate() + 1); // Exclusive end date
    fetchReport(start, end);
  });
}
