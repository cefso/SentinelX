import { AlertResponse } from '@/types/alert'
import { formatLocalDateTime } from './datetime'

/**
 * 处理 CSV 字段转义
 */
function escapeCSVField(field: string | number | null | undefined): string {
  if (field === null || field === undefined) {
    return ''
  }
  const str = String(field)
  // 如果包含逗号、引号或换行符，需要用引号包裹
  if (str.includes(',') || str.includes('"') || str.includes('\n') || str.includes('\r')) {
    // 双引号转义
    return `"${str.replace(/"/g, '""')}"`
  }
  return str
}

/**
 * 格式化处置记录为 CSV 友好格式
 * 格式：[时间] 操作人: 备注; [时间] 操作人: 备注
 */
function formatDisposeRecords(records: AlertResponse['dispose_records']): string {
  if (!records || records.length === 0) {
    return ''
  }

  return records
    .map(record => {
      const time = formatLocalDateTime(record.created_at)
      const operator = record.operator_name || '未知'
      const comment = record.comment || ''
      return `[${time}] ${operator}: ${comment}`
    })
    .join('; ')
}

/**
 * CSV 列定义
 */
export const CSV_COLUMNS = [
  { key: 'id', label: 'ID' },
  { key: 'title', label: '告警标题' },
  { key: 'severity', label: '严重级别' },
  { key: 'status', label: '状态' },
  { key: 'source_name', label: '来源' },
  { key: 'namespace', label: '命名空间' },
  { key: 'instance', label: '实例' },
  { key: 'fingerprint', label: '指纹' },
  { key: 'fired_at', label: '触发时间' },
  { key: 'fire_count', label: '触发次数' },
  { key: 'dispose_records', label: '处置记录' },
  { key: 'assignee_name', label: '处理人' },
] as const

/**
 * 将告警数据转换为 CSV 行
 */
function alertToRow(alert: AlertResponse): Record<string, any> {
  return {
    id: alert.id,
    title: alert.title,
    severity: alert.severity,
    status: alert.status,
    source_name: alert.source_name || alert.source,
    namespace: alert.namespace || '',
    instance: alert.instance_name || alert.instance_id || '',
    fingerprint: alert.fingerprint,
    fired_at: alert.fired_at ? formatLocalDateTime(alert.fired_at) : '',
    fire_count: alert.fire_count,
    dispose_records: formatDisposeRecords(alert.dispose_records),
    assignee_name: alert.assignee_name || '',
  }
}

/**
 * 将数据转换为 CSV 字符串
 */
export function convertToCSV(alerts: AlertResponse[]): string {
  // CSV 表头
  const headers = CSV_COLUMNS.map(col => escapeCSVField(col.label)).join(',')

  // CSV 数据行
  const rows = alerts.map(alert => {
    const row = alertToRow(alert)
    return CSV_COLUMNS.map(col => escapeCSVField(row[col.key])).join(',')
  })

  // 添加 BOM 头以支持中文 Excel 打开
  const BOM = '\uFEFF'
  return BOM + headers + '\n' + rows.join('\n')
}

/**
 * 触发浏览器下载 CSV 文件
 */
export function downloadCSV(filename: string, csvContent: string): void {
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = filename
  link.style.display = 'none'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(link.href)
}

/**
 * 生成导出文件名
 */
export function generateExportFilename(): string {
  const now = new Date()
  const year = now.getFullYear()
  const month = String(now.getMonth() + 1).padStart(2, '0')
  const day = String(now.getDate()).padStart(2, '0')
  const hours = String(now.getHours()).padStart(2, '0')
  const minutes = String(now.getMinutes()).padStart(2, '0')
  const seconds = String(now.getSeconds()).padStart(2, '0')
  return `告警记录_${year}-${month}-${day}_${hours}${minutes}${seconds}.csv`
}
