import { format } from 'date-fns'
import { zhCN } from 'date-fns/locale'

export function formatLocalDateTime(utcDate: string, fmt: string = 'yyyy-MM-dd HH:mm:ss'): string {
  // Parse as UTC, then format in local timezone
  const date = new Date(utcDate)
  return format(date, fmt, { locale: zhCN })
}
