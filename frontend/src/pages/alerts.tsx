import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { apiClient } from '@/services/api'
import { AlertResponse, AlertStats, AlertAggregatedItem } from '@/types/alert'
import { useCloudMetricsMap } from '@/hooks/useCloudMetrics'
import { formatLocalDateTime } from '@/utils/datetime'
import { convertToCSV, downloadCSV, generateExportFilename } from '@/utils/export'
import { ExportModal, ExportRange } from '@/components/alerts/ExportModal'
import { AdvancedFilters, AdvancedFilterState } from '@/components/alerts/AdvancedFilters'
import { toast } from '@/stores/toast-store'

/**
 * 从聚合项中提取 AlertResponse
 */
function extractAlertFromAggregated(item: AlertAggregatedItem | AlertResponse): AlertResponse {
  if ('latest' in item && item.latest) {
    return item.latest
  }
  return item as AlertResponse
}

interface AlertSource {
  id: number
  name: string
  code: string
  source_type: string
  config: Record<string, any>
  description?: string
  is_active: boolean
  alert_count: number
  last_alert_at?: string
  created_at: string
}
import { Bell, AlertTriangle, AlertCircle, XCircle, ChevronLeft, ChevronRight, Search, RotateCcw, Fingerprint, Layers, ScrollText, Zap, Clock, Download, ArrowUp, ArrowDown } from 'lucide-react'
import { SeverityBadge, StatusBadge } from '@/components/common/Badges'
import { WebhookLogModal } from '@/components/common/WebhookLogModal'

export function AlertsPage() {
  const navigate = useNavigate()
  const [page, setPage] = useState(1)
  const [pageSize] = useState(20)
  const [searchParams] = useSearchParams()
  const [filters, setFilters] = useState({
    status: '',
    severity: '',
    sourceId: '' as number | '',
    keyword: '',
    fingerprint: '',
  })
  const [aggregateMode, setAggregateMode] = useState(true)
  const [showWebhookLogModal, setShowWebhookLogModal] = useState(false)
  const [showExportModal, setShowExportModal] = useState(false)
  const [isExporting, setIsExporting] = useState(false)
  const [sortBy, setSortBy] = useState<'duration' | 'severity' | 'count'>('duration')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')
  const [advancedFilters, setAdvancedFilters] = useState<AdvancedFilterState>({
    startTime: '',
    endTime: '',
    maxFiredAt: '',
    flappingOnly: false,
    staleOnly: false,
    assigneeId: '',
  })

  // 查询未忽略的 Webhook 错误日志数量
  const { data: webhookLogCountData } = useQuery({
    queryKey: ['webhook-logs-count'],
    queryFn: () => apiClient.getWebhookLogs({ dismissed: false, page_size: 1 }),
    refetchInterval: 30000, // 30秒轮询
  })

  // 初始化从 URL 参数
  useEffect(() => {
    const fp = searchParams.get('fingerprint')
    const agg = searchParams.get('aggregate')
    if (fp) {
      setFilters(prev => ({ ...prev, fingerprint: fp }))
      setPage(1)
    }
    if (agg === 'false') {
      setAggregateMode(false)
    }
  }, [searchParams])

  const { data: stats } = useQuery<AlertStats>({
    queryKey: ['alertStats'],
    queryFn: () => apiClient.get('/alerts/stats'),
  })

  const { data: sources = [] } = useQuery<AlertSource[]>({
    queryKey: ['alert-sources'],
    queryFn: () => apiClient.get('/sources'),
  })

  // 查询去重后的触发中告警数量
  const { data: firingAlerts } = useQuery<{ items: AlertAggregatedItem[]; total: number }>({
    queryKey: ['alerts-dedup', 'firing'],
    queryFn: () => apiClient.get('/alerts', {
      page: 1,
      page_size: 1,
      status: 'firing',
      aggregate: true,
    }),
  })

  // 查询去重后的 Critical 告警数量
  const { data: criticalAlerts } = useQuery<{ items: AlertAggregatedItem[]; total: number }>({
    queryKey: ['alerts-dedup', 'critical'],
    queryFn: () => apiClient.get('/alerts', {
      page: 1,
      page_size: 1,
      status: 'firing',
      severity: 'critical',
      aggregate: true,
    }),
  })

  // 查询去重后的 High 告警数量
  const { data: highAlerts } = useQuery<{ items: AlertAggregatedItem[]; total: number }>({
    queryKey: ['alerts-dedup', 'high'],
    queryFn: () => apiClient.get('/alerts', {
      page: 1,
      page_size: 1,
      status: 'firing',
      severity: 'high',
      aggregate: true,
    }),
  })

  const { data: alerts, isLoading, refetch } = useQuery<{ items: AlertResponse[]; total: number; page: number; page_size: number }>({
    queryKey: ['alerts', page, pageSize, filters, aggregateMode, sortBy, sortOrder, advancedFilters],
    queryFn: () => apiClient.get('/alerts', {
      page,
      page_size: pageSize,
      status: filters.status || undefined,
      severity: filters.severity || undefined,
      source_id: filters.sourceId || undefined,
      keyword: filters.keyword || undefined,
      fingerprint: filters.fingerprint || undefined,
      aggregate: aggregateMode || undefined,
      hide_aggregated_children: false,
      sort_by: sortBy,
      sort_order: sortOrder,
      start_time: advancedFilters.startTime || undefined,
      end_time: advancedFilters.endTime || undefined,
      max_fired_at: advancedFilters.maxFiredAt || undefined,
      flapping_only: advancedFilters.flappingOnly || undefined,
      stale_only: advancedFilters.staleOnly || undefined,
      assignee_id: advancedFilters.assigneeId || undefined,
    }),
  })

  const { data: cloudMetricsMap } = useCloudMetricsMap()

  const { data: users = [] } = useQuery<{ id: number; username: string }[]>({
    queryKey: ['users-for-assign'],
    queryFn: () => apiClient.get('/users'),
  })

  const getProductDisplayName = (namespace: string) => {
    if (!cloudMetricsMap || !namespace) return namespace || '-'
    const records = cloudMetricsMap[namespace]
    // 优先使用 namespace_desc，否则使用 product，否则使用原始 namespace
    return records?.[0]?.namespace_desc || records?.[0]?.product || namespace || '-'
  }

  const getSourceDisplayName = (alert: Pick<AlertResponse, 'source' | 'source_name'>) =>
    alert.source_name || alert.source

  const totalPages = Math.ceil((alerts?.total || 0) / pageSize)

  // 导出处理函数
  const handleExport = async (range: ExportRange, customDates?: { start: string; end: string }) => {
    setIsExporting(true)
    try {
      let allAlerts: AlertResponse[] = []

      // 构建查询参数
      const baseParams: Record<string, any> = {
        status: filters.status || undefined,
        severity: filters.severity || undefined,
        source_id: filters.sourceId || undefined,
        keyword: filters.keyword || undefined,
        fingerprint: filters.fingerprint || undefined,
      }

      if (range === 'current_page') {
        // 导出当前页 - 需要处理聚合模式
        const items = alerts?.items || []
        allAlerts = items.map(item => extractAlertFromAggregated(item as AlertAggregatedItem | AlertResponse))
      } else {
        // 获取所有数据
        let currentPage = 1
        let hasMore = true

        while (hasMore) {
          const params: Record<string, any> = {
            ...baseParams,
            page: currentPage,
            page_size: 100,
            aggregate: false,
          }

          // 添加时间范围筛选
          if (range === 'last_7_days') {
            const sevenDaysAgo = new Date()
            sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7)
            params.start_time = sevenDaysAgo.toISOString()
          } else if (range === 'last_30_days') {
            const thirtyDaysAgo = new Date()
            thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30)
            params.start_time = thirtyDaysAgo.toISOString()
          } else if (range === 'custom' && customDates) {
            params.start_time = new Date(customDates.start).toISOString()
            params.end_time = new Date(customDates.end + 'T23:59:59').toISOString()
          }

          const result = await apiClient.getAlertsForExport(params)
          allAlerts = [...allAlerts, ...result.items]

          if (allAlerts.length >= result.total || result.items.length === 0) {
            hasMore = false
          } else {
            currentPage++
          }
        }
      }

      if (allAlerts.length === 0) {
        toast.warning('没有可导出的告警记录')
        return
      }

      // 为每条告警获取处置记录
      const alertsWithRecords = await Promise.all(
        allAlerts.map(async (alert) => {
          try {
            const records = await apiClient.getDisposeRecords(alert.id)
            return { ...alert, dispose_records: records }
          } catch {
            return { ...alert, dispose_records: [] }
          }
        })
      )

      // 转换为 CSV 并下载
      const csv = convertToCSV(alertsWithRecords)
      const filename = generateExportFilename()
      downloadCSV(filename, csv)

      toast.success(`成功导出 ${allAlerts.length} 条告警记录`)
      setShowExportModal(false)
    } catch (error) {
      console.error('Export failed:', error)
      toast.error('导出失败，请重试')
    } finally {
      setIsExporting(false)
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">告警列表</h1>
          <p className="text-sm text-gray-500 mt-0.5">查看和管理所有告警，支持指纹视图和明细视图</p>
        </div>
        <button
          onClick={() => setShowWebhookLogModal(true)}
          className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-200 rounded-lg hover:bg-gray-50"
        >
          <ScrollText className="w-4 h-4" />
          Webhook 日志
          {(webhookLogCountData?.total || 0) > 0 && (
            <span className="px-2 py-0.5 text-xs font-medium text-white bg-orange-500 rounded-full">
              {webhookLogCountData?.total}
            </span>
          )}
        </button>
      </div>

      {/* 统计卡片 - 5个带渐变和图标 */}
      <div className="grid grid-cols-5 gap-4">
        <StatCard
          title="总告警"
          value={stats?.total || 0}
          subtitle="全部告警"
          icon={Bell}
          gradient="from-blue-500 to-blue-600"
        />
        <StatCard
          title="去重告警"
          value={stats?.unique || 0}
          subtitle="不同指纹"
          icon={Fingerprint}
          gradient="from-purple-500 to-purple-600"
        />
        <StatCard
          title="触发中"
          value={firingAlerts?.total || 0}
          subtitle="正在触发"
          icon={AlertTriangle}
          gradient="from-orange-500 to-orange-600"
        />
        <StatCard
          title="Critical"
          value={criticalAlerts?.total || 0}
          subtitle="严重级别"
          icon={XCircle}
          gradient="from-red-500 to-red-600"
        />
        <StatCard
          title="High"
          value={highAlerts?.total || 0}
          subtitle="高级别"
          icon={AlertCircle}
          gradient="from-amber-500 to-amber-600"
        />
      </div>

      <div className="bg-white rounded-lg shadow">
        {/* 过滤栏 - 分段控件风格 */}
        <div className="p-4 border-b space-y-3">
          <div className="flex gap-3 items-center">
            <Search className="w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="搜索告警标题或内容..."
              className="flex-1 px-3 py-2 border rounded-md"
              value={filters.keyword}
              onChange={(e) => setFilters({ ...filters, keyword: e.target.value })}
            />
            <button
              onClick={() => { setPage(1); refetch(); }}
              className="px-4 py-2 bg-primary text-white rounded-md hover:bg-primary/90"
            >
              搜索
            </button>
            <button
              onClick={() => setFilters({ status: '', severity: '', sourceId: '', keyword: '', fingerprint: '' })}
              className="px-4 py-2 border rounded-md hover:bg-gray-50 flex items-center gap-1"
            >
              <RotateCcw className="w-3 h-3" />
              重置
            </button>
            <button
              onClick={() => setShowExportModal(true)}
              className="px-4 py-2 border rounded-md hover:bg-gray-50 flex items-center gap-1"
            >
              <Download className="w-4 h-4" />
              导出
            </button>
          </div>

          <div className="flex gap-2 flex-wrap items-center">
            {/* 列表视图切换（按 fingerprint 分组，与策略聚合规则无关） */}
            <span className="text-sm text-gray-500 py-1.5">视图:</span>
            <div className="flex gap-1 bg-gray-100 p-1 rounded-lg">
              {[
                { value: true, label: '指纹视图' },
                { value: false, label: '明细视图' },
              ].map(opt => (
                <button
                  key={String(opt.value)}
                  onClick={() => { setAggregateMode(opt.value); setPage(1); }}
                  className={`px-3 py-1 text-sm rounded-md transition-colors ${
                    aggregateMode === opt.value
                      ? 'bg-white shadow text-gray-900 font-medium'
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>

            <span className="text-sm text-gray-500 py-1.5">排序:</span>
            <div className="flex gap-1 bg-gray-100 p-1 rounded-lg">
              {[
                { value: 'duration', label: '触发时间' },
                { value: 'severity', label: '严重级别' },
                { value: 'count', label: '告警数量' },
              ].map(opt => (
                <button
                  key={opt.value}
                  onClick={() => setSortBy(opt.value as any)}
                  className={`px-3 py-1 text-sm rounded-md transition-colors ${
                    sortBy === opt.value
                      ? 'bg-white shadow text-gray-900 font-medium'
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
            <button
              onClick={() => setSortOrder(prev => prev === 'asc' ? 'desc' : 'asc')}
              className="p-1.5 border rounded hover:bg-gray-50"
              title={sortOrder === 'asc' ? '升序' : '降序'}
            >
              {sortOrder === 'asc' ? <ArrowUp className="w-4 h-4" /> : <ArrowDown className="w-4 h-4" />}
            </button>

            <span className="text-sm text-gray-500 py-1.5">状态:</span>
            <div className="flex gap-1 bg-gray-100 p-1 rounded-lg">
              {[
                { value: '', label: '全部' },
                { value: 'firing', label: '触发中' },
                { value: 'resolved', label: '已恢复' },
                { value: 'suppressed', label: '已抑制' },
                { value: 'deduplicated', label: '已去重' },
                { value: 'aggregated', label: '已聚合' },
                { value: 'acknowledged', label: '已确认' },
              ].map(opt => (
                <button
                  key={opt.value}
                  onClick={() => { setFilters({ ...filters, status: opt.value }); setPage(1); }}
                  className={`px-3 py-1 text-sm rounded-md transition-colors ${
                    filters.status === opt.value
                      ? 'bg-white shadow text-gray-900 font-medium'
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>

            <span className="text-sm text-gray-500 py-1.5">级别:</span>
            <div className="flex gap-1 bg-gray-100 p-1 rounded-lg">
              {[
                { value: '', label: '全部' },
                { value: 'critical', label: '严重' },
                { value: 'high', label: '重要' },
                { value: 'medium', label: '次要' },
                { value: 'low', label: '提示' },
              ].map(opt => (
                <button
                  key={opt.value}
                  onClick={() => { setFilters({ ...filters, severity: opt.value }); setPage(1); }}
                  className={`px-3 py-1 text-sm rounded-md transition-colors ${
                    filters.severity === opt.value
                      ? 'bg-white shadow text-gray-900 font-medium'
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>

            <span className="text-sm text-gray-500 py-1.5">来源:</span>
            <div className="flex gap-1 bg-gray-100 p-1 rounded-lg">
              <button
                key="all"
                onClick={() => { setFilters({ ...filters, sourceId: '' }); setPage(1); }}
                className={`px-3 py-1 text-sm rounded-md transition-colors ${
                  filters.sourceId === ''
                    ? 'bg-white shadow text-gray-900 font-medium'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                全部
              </button>
              {sources.map(source => (
                <button
                  key={source.id}
                  onClick={() => { setFilters({ ...filters, sourceId: source.id }); setPage(1); }}
                  className={`px-3 py-1 text-sm rounded-md transition-colors ${
                    filters.sourceId === source.id
                      ? 'bg-white shadow text-gray-900 font-medium'
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  {source.name}
                </button>
              ))}
            </div>

            {/* 指纹搜索 */}
            <div className="flex items-center gap-2 ml-auto">
              <input
                type="text"
                placeholder="搜索指纹..."
                value={filters.fingerprint}
                onChange={(e) => { setFilters({ ...filters, fingerprint: e.target.value }); setPage(1); }}
                className="px-3 py-1 text-sm border rounded-md w-48"
              />
            </div>
          </div>

          {/* 高级筛选 */}
          <div className="mt-3">
            <AdvancedFilters
              filters={advancedFilters}
              onFilterChange={(newFilters) => {
                setAdvancedFilters(newFilters)
                setPage(1)
              }}
              users={users}
            />
          </div>
        </div>

        {/* 告警列表 - 表格布局 */}
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead>
              <tr className="bg-gray-50">
                <th className="px-3 py-2.5 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-12">#</th>
                <th className="px-3 py-2.5 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">告警名称</th>
                <th className="px-3 py-2.5 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-24">级别</th>
                <th className="px-3 py-2.5 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-28">来源</th>
                <th className="px-3 py-2.5 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">命名空间</th>
                <th className="px-3 py-2.5 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">实例</th>
                <th className="px-3 py-2.5 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-40">时间</th>
                <th className="px-3 py-2.5 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-20">状态</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {isLoading ? (
                <tr>
                  <td colSpan={8} className="px-3 py-8 text-center text-gray-500">加载中...</td>
                </tr>
              ) : alerts?.items.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-3 py-8 text-center text-gray-500">暂无告警</td>
                </tr>
              ) : aggregateMode ? (
                (alerts?.items as unknown as AlertAggregatedItem[] || []).map((item, idx) => {
                  const isStrategyGroup = item.row_type === 'strategy_group'
                  return (
                  <tr
                    key={isStrategyGroup ? `strategy-group-${item.aggregate_group_id}` : item.fingerprint}
                    className={`hover:bg-gray-50 cursor-pointer ${isStrategyGroup ? 'bg-violet-50/20' : ''}`}
                    onClick={() => navigate(`/alerts/${item.latest.id}`)}
                  >
                    <td className="px-3 py-2 text-sm text-gray-400">{(page - 1) * pageSize + idx + 1}</td>
                    <td className="px-3 py-2">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-gray-900 truncate max-w-md">{item.latest.title}</span>
                        {item.flapping && (
                          <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 text-xs font-medium bg-orange-100 text-orange-700 rounded animate-pulse shrink-0">
                            <Zap className="w-3 h-3" />
                            抖动
                          </span>
                        )}
                        {item.stale && (
                          <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 text-xs font-medium bg-gray-100 text-gray-600 rounded shrink-0">
                            <Clock className="w-3 h-3" />
                            长时间未更新
                          </span>
                        )}
                        <span className={`flex items-center gap-0.5 text-xs px-1.5 py-0.5 rounded font-medium ${
                          isStrategyGroup
                            ? 'bg-violet-100 text-violet-700'
                            : 'bg-purple-100 text-purple-700'
                        }`}>
                          {isStrategyGroup ? <Layers className="w-3 h-3" /> : <Fingerprint className="w-3 h-3" />}
                          ×{item.count}
                        </span>
                        {isStrategyGroup && (
                          <span className="flex items-center gap-0.5 text-xs bg-violet-100 text-violet-700 px-1.5 py-0.5 rounded font-medium">
                            <Layers className="w-3 h-3" />
                            策略×{item.count}
                          </span>
                        )}
                        {!isStrategyGroup && (item.latest.aggregate_group_count ?? 0) > 1 && (
                          <span className="flex items-center gap-0.5 text-xs bg-violet-100 text-violet-700 px-1.5 py-0.5 rounded font-medium">
                            <Layers className="w-3 h-3" />
                            策略×{item.latest.aggregate_group_count}
                          </span>
                        )}
                      </div>
                      <div className="text-xs text-gray-400 mt-0.5 font-mono truncate max-w-md">
                        {isStrategyGroup
                          ? (item.group_label ? `策略聚合组 · ${item.group_label}` : '策略聚合组 · 含多个指纹')
                          : item.fingerprint}
                      </div>
                    </td>
                    <td className="px-3 py-2"><SeverityBadge severity={item.latest.severity} /></td>
                    <td className="px-3 py-2 text-sm text-gray-500">{getSourceDisplayName(item.latest)}</td>
                    <td className="px-3 py-2 text-sm text-gray-500 truncate max-w-32">{getProductDisplayName(item.latest.namespace || '')}</td>
                    <td className="px-3 py-2 text-sm text-gray-500 truncate max-w-32">{item.latest.instance_name || item.latest.instance_id || '-'}</td>
                    <td className="px-3 py-2 text-sm text-gray-500 whitespace-nowrap">
                      {item.latest.fired_at ? formatLocalDateTime(item.latest.fired_at) : '-'}
                    </td>
                    <td className="px-3 py-2 whitespace-nowrap w-20"><StatusBadge status={item.latest.status} /></td>
                  </tr>
                  )
                })
              ) : (
                alerts?.items?.map((alert, idx) => (
                  <tr
                    key={alert.id}
                    className="hover:bg-gray-50 cursor-pointer"
                    onClick={() => navigate(`/alerts/${alert.id}`)}
                  >
                    <td className="px-3 py-2 text-sm text-gray-400">{(page - 1) * pageSize + idx + 1}</td>
                    <td className="px-3 py-2">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-gray-900 truncate max-w-md">{alert.title}</span>
                        {alert.fire_count > 1 && (
                          <span className="text-xs text-orange-500 font-medium">×{alert.fire_count}</span>
                        )}
                        {(alert.aggregate_group_count ?? 0) > 1 && (
                          <span className="flex items-center gap-0.5 text-xs bg-violet-100 text-violet-700 px-1.5 py-0.5 rounded font-medium">
                            <Layers className="w-3 h-3" />
                            策略×{alert.aggregate_group_count}
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-3 py-2"><SeverityBadge severity={alert.severity} /></td>
                    <td className="px-3 py-2 text-sm text-gray-500">{getSourceDisplayName(alert)}</td>
                    <td className="px-3 py-2 text-sm text-gray-500 truncate max-w-32">{getProductDisplayName(alert.namespace || '')}</td>
                    <td className="px-3 py-2 text-sm text-gray-500 truncate max-w-32">{alert.instance_name || alert.instance_id || '-'}</td>
                    <td className="px-3 py-2 text-sm text-gray-500 whitespace-nowrap">
                      {alert.fired_at ? formatLocalDateTime(alert.fired_at) : '-'}
                    </td>
                    <td className="px-3 py-2 whitespace-nowrap w-20"><StatusBadge status={alert.status} /></td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* 紧凑分页 */}
        {totalPages > 1 && (
          <div className="px-4 py-3 border-t flex items-center justify-between">
            <div className="text-sm text-gray-500">
              共 {alerts?.total} 条，第 {page} / {totalPages} 页
            </div>
            <div className="flex items-center gap-1">
              <button
                disabled={page <= 1}
                onClick={() => setPage(p => Math.max(1, p - 1))}
                className="p-1.5 border rounded hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                let pageNum: number
                if (totalPages <= 5) {
                  pageNum = i + 1
                } else if (page <= 3) {
                  pageNum = i + 1
                } else if (page >= totalPages - 2) {
                  pageNum = totalPages - 4 + i
                } else {
                  pageNum = page - 2 + i
                }
                return (
                  <button
                    key={pageNum}
                    onClick={() => setPage(pageNum)}
                    className={`w-8 h-8 text-sm rounded border ${
                      page === pageNum
                        ? 'bg-primary text-white border-primary'
                        : 'hover:bg-gray-50'
                    }`}
                  >
                    {pageNum}
                  </button>
                )
              })}
              <button
                disabled={page >= totalPages}
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                className="p-1.5 border rounded hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Webhook 日志弹窗 */}
      <WebhookLogModal
        open={showWebhookLogModal}
        onOpenChange={setShowWebhookLogModal}
      />

      {/* 导出弹窗 */}
      <ExportModal
        open={showExportModal}
        onOpenChange={setShowExportModal}
        currentCount={alerts?.items?.length || 0}
        totalCount={alerts?.total || 0}
        onExport={handleExport}
        isExporting={isExporting}
      />
    </div>
  )
}

function StatCard({
  title,
  value,
  subtitle,
  icon: Icon,
  gradient,
}: {
  title: string
  value: number
  subtitle: string
  icon: React.ComponentType<{ className?: string }>
  gradient: string
}) {
  return (
    <div className={`rounded-xl bg-gradient-to-br ${gradient} p-4 text-white shadow-sm`}>
      <div className="flex items-start justify-between">
        <div>
          <div className="text-sm font-medium opacity-80">{title}</div>
          <div className="text-2xl font-bold mt-0.5">{value.toLocaleString()}</div>
          <div className="text-xs opacity-60 mt-0.5">{subtitle}</div>
        </div>
        <div className="p-2 bg-white/20 rounded-lg">
          <Icon className="w-5 h-5" />
        </div>
      </div>
    </div>
  )
}

