export function formatCurrency(value, decimals = 0) {
  if (value === null || value === undefined) return '₹0';
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);
}

export function formatDate(dateString, options = 'short') {
  if (!dateString) return '--';
  const date = new Date(dateString);
  if (options === 'short') {
    return date.toLocaleDateString('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    });
  }
  return date.toLocaleDateString('en-IN');
}

export function formatNumber(value, decimals = 2) {
  if (value === null || value === undefined) return '0';
  return value.toFixed(decimals);
}

export function formatPercent(value) {
  if (value === null || value === undefined) return '0%';
  return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
}