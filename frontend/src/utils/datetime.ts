export function formatLocalDateTime(utcDate: string): string {
  const date = new Date(utcDate)
  return date.toLocaleString('zh-CN', {
    timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  })
}
