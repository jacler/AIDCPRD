export function formatNumber(value: number): string {
  return value.toLocaleString("zh-CN", { maximumFractionDigits: 0 });
}

export function formatCurrency(value: number): string {
  if (value >= 100_000_000) {
    return `¥${(value / 100_000_000).toFixed(2)}亿`;
  }
  if (value >= 10_000) {
    return `¥${(value / 10_000).toFixed(1)}万`;
  }
  return `¥${formatNumber(value)}`;
}

export function formatCurrencyFull(value: number): string {
  return `¥ ${formatNumber(value)}`;
}

export function formatPercent(value: number, total: number): string {
  if (total <= 0) return "0%";
  return `${((value / total) * 100).toFixed(1)}%`;
}

export function formatRelativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const minutes = Math.floor(diff / 60_000);
  if (minutes < 1) return "刚刚";
  if (minutes < 60) return `${minutes} 分钟前`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} 小时前`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days} 天前`;
  return new Date(iso).toLocaleDateString("zh-CN");
}
