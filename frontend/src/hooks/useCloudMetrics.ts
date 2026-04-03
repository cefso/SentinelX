import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { apiClient, CloudMetricRecord } from '@/services/api'
import { AlertResponse } from '@/types/alert'

// ============ Cloud Metrics Map (fetched from API) ============

export interface CloudMetricsMap {
  [namespace: string]: CloudMetricRecord[]
}

/**
 * Fetch and cache cloud metrics map from API, grouped by namespace.
 */
export function useCloudMetricsMap() {
  return useQuery<Record<string, CloudMetricRecord[]>>({
    queryKey: ['cloudMetricsMap'],
    queryFn: () => apiClient.getCloudMetricsMap(),
    staleTime: 10 * 60 * 1000, // 10 minutes
  })
}

/**
 * Get product Chinese name for a given namespace.
 */
export function useProductName(namespace: string, map?: Record<string, CloudMetricRecord[]>): string {
  return useMemo(() => {
    if (!map || !namespace) return ''
    const records = map[namespace]
    if (!records?.length) return ''
    return records[0].product || ''
  }, [map, namespace])
}

/**
 * Get metric Chinese description for a given namespace + metricName.
 */
export function useMetricDesc(
  namespace: string,
  metricName: string,
  map?: Record<string, CloudMetricRecord[]>
): string {
  return useMemo(() => {
    if (!map || !namespace || !metricName) return ''
    const records = map[namespace]
    if (!records) return ''
    const record = records.find(m => m.metric_name === metricName)
    return record?.metric_desc || ''
  }, [map, namespace, metricName])
}

// ============ Alert label extraction ============

export interface CloudMetricInfo {
  product: string
  instance: string
  source: string
}

/**
 * Extract normalized cloud product/instance info from alert labels.
 * Maps different cloud provider label schemas to consistent product/instance.
 */
export function useCloudMetrics(alerts: AlertResponse[]): Record<number, CloudMetricInfo> {
  return useMemo(() => {
    const result: Record<number, CloudMetricInfo> = {}
    for (const alert of alerts) {
      const labels = alert.labels || {}
      const source = alert.source || ''

      let product = ''
      let instance = ''

      if (source === 'aliyun_cms') {
        product = (labels.namespace || '') as string
        instance = (labels.instance_name || labels.instance_id || '') as string
      } else if (source === 'aliyun_cms2') {
        product = (labels.namespace || labels.metric_name || '') as string
        instance = (labels.metric_name || '') as string
      } else if (source === 'tencent') {
        product = (labels.appid || '') as string
        instance = (labels.region || '') as string
      } else if (source === 'aliyun') {
        product = (labels.product || labels.region || '') as string
        instance = (labels.instanceId || labels.resource_group_id || '') as string
      } else if (source === 'zabbix') {
        product = (labels.trigger_name || labels.host || '') as string
        instance = (labels.host || '') as string
      } else if (source === 'alertmanager' || source === 'prometheus') {
        product = (labels.alertname || labels.job || '') as string
        instance = (labels.instance || labels.export_name || '') as string
      }

      result[alert.id] = { product, instance, source }
    }
    return result
  }, [alerts])
}
