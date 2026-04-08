import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient, CloudMetricRecord, CloudProductMetricInput } from '@/services/api'
import { EditModal } from './components/EditModal'
import { Loader2, Plus, RefreshCw, Search, X, ChevronDown, ChevronRight } from 'lucide-react'

const PAGE_SIZE = 20

export function CloudMetricsPage() {
  const queryClient = useQueryClient()
  const [page, setPage] = useState(1)
  const [productSearch, setProductSearch] = useState('')
  const [namespaceSearch, setNamespaceSearch] = useState('')
  const [showModal, setShowModal] = useState(false)
  const [editingMetric, setEditingMetric] = useState<CloudMetricRecord | null>(null)
  const [expandedRow, setExpandedRow] = useState<number | null>(null)
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())
  const [showBatchDeleteConfirm, setShowBatchDeleteConfirm] = useState(false)
  const [statusFilter, setStatusFilter] = useState<'all' | 'active' | 'inactive'>('active')

  const { data, isLoading, isFetching } = useQuery({
    queryKey: ['cloud-metrics', page, productSearch, namespaceSearch, statusFilter],
    queryFn: () =>
      apiClient.getCloudMetrics({
        page,
        page_size: PAGE_SIZE,
        product: productSearch || undefined,
        namespace: namespaceSearch || undefined,
        status: statusFilter,
      }),
    placeholderData: (prev) => prev,
  })

  const syncAllMutation = useMutation({
    mutationFn: () => apiClient.syncAllCloudMetrics(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cloud-metrics'] })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => apiClient.deleteCloudMetric(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cloud-metrics'] })
      queryClient.invalidateQueries({ queryKey: ['cloudMetricsMap'] })
    },
  })

  const batchDeleteMutation = useMutation({
    mutationFn: (ids: number[]) => apiClient.batchDeleteCloudMetrics(ids),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cloud-metrics'] })
      queryClient.invalidateQueries({ queryKey: ['cloudMetricsMap'] })
      setSelectedIds(new Set())
      setShowBatchDeleteConfirm(false)
    },
  })

  const toggleActiveMutation = useMutation({
    mutationFn: ({ id, is_active }: { id: number; is_active: number }) =>
      apiClient.updateCloudMetric(id, { is_active } as Partial<CloudProductMetricInput>),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cloud-metrics'] })
      queryClient.invalidateQueries({ queryKey: ['cloudMetricsMap'] })
    },
  })

  const handleCreate = () => {
    setEditingMetric(null)
    setShowModal(true)
  }

  const handleEdit = (metric: CloudMetricRecord) => {
    setEditingMetric(metric)
    setShowModal(true)
  }

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0

  const handleSearch = () => {
    setPage(1)
  }

  const clearSearch = () => {
    setProductSearch('')
    setNamespaceSearch('')
    setPage(1)
  }

  const toggleSelectAll = () => {
    if (!data?.items) return
    if (selectedIds.size === data.items.length) {
      setSelectedIds(new Set())
    } else {
      setSelectedIds(new Set(data.items.map((m) => m.id)))
    }
  }

  const toggleSelect = (id: number) => {
    const newSelected = new Set(selectedIds)
    if (newSelected.has(id)) {
      newSelected.delete(id)
    } else {
      newSelected.add(id)
    }
    setSelectedIds(newSelected)
  }

  const handleBatchDelete = () => {
    if (selectedIds.size === 0) return
    setShowBatchDeleteConfirm(true)
  }

  const confirmBatchDelete = () => {
    batchDeleteMutation.mutate(Array.from(selectedIds))
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">云产品指标管理</h1>
          <p className="text-gray-600">管理云产品监控指标的中文描述和启用状态</p>
        </div>
        <div className="flex gap-2">
          {selectedIds.size > 0 && (
            <button
              onClick={handleBatchDelete}
              disabled={batchDeleteMutation.isPending}
              className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 flex items-center gap-2 disabled:opacity-50"
            >
              {batchDeleteMutation.isPending ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <X className="w-4 h-4" />
              )}
              批量删除 ({selectedIds.size})
            </button>
          )}
          <button
            onClick={() => syncAllMutation.mutate()}
            disabled={syncAllMutation.isPending}
            className="px-4 py-2 border rounded-md hover:bg-gray-50 flex items-center gap-2 disabled:opacity-50"
          >
            {syncAllMutation.isPending ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <RefreshCw className="w-4 h-4" />
            )}
            全量同步
          </button>
          <button
            onClick={handleCreate}
            className="px-4 py-2 bg-primary text-white rounded-md hover:bg-primary/90 flex items-center gap-2"
          >
            <Plus className="w-4 h-4" />
            新增指标
          </button>
        </div>
      </div>

      {/* Search filters */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex gap-4 items-end">
          <div className="flex-1">
            <label className="block text-sm font-medium text-gray-700 mb-1">产品名称</label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                value={productSearch}
                onChange={(e) => setProductSearch(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                placeholder="搜索产品名称..."
                className="w-full pl-9 pr-8 py-2 border rounded-md text-sm"
              />
              {productSearch && (
                <button
                  onClick={() => { setProductSearch(''); setPage(1) }}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                >
                  <X className="w-4 h-4" />
                </button>
              )}
            </div>
          </div>
          <div className="flex-1">
            <label className="block text-sm font-medium text-gray-700 mb-1">命名空间</label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                value={namespaceSearch}
                onChange={(e) => setNamespaceSearch(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                placeholder="搜索命名空间..."
                className="w-full pl-9 pr-8 py-2 border rounded-md text-sm"
              />
              {namespaceSearch && (
                <button
                  onClick={() => { setNamespaceSearch(''); setPage(1) }}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                >
                  <X className="w-4 h-4" />
                </button>
              )}
            </div>
          </div>
          <button
            onClick={handleSearch}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm"
          >
            搜索
          </button>
          {(productSearch || namespaceSearch) && (
            <button
              onClick={clearSearch}
              className="px-4 py-2 border rounded-md hover:bg-gray-50 text-sm"
            >
              清除
            </button>
          )}
        </div>
        {/* 状态筛选 */}
        <div className="flex gap-2 mt-3">
          <span className="text-sm text-gray-500">状态:</span>
          {(['all', 'active', 'inactive'] as const).map((s) => (
            <button
              key={s}
              onClick={() => { setStatusFilter(s); setPage(1) }}
              className={`px-3 py-1 text-sm rounded ${
                statusFilter === s
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {s === 'all' ? '全部' : s === 'active' ? '启用' : '停用'}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-gray-500">
            <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2" />
            加载中...
          </div>
        ) : !data || !data.items || data.items.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            {productSearch || namespaceSearch ? '未找到匹配的指标' : '暂无指标数据'}
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-500 w-8">
                      <input
                        type="checkbox"
                        checked={data?.items?.length ? selectedIds.size === data.items.length : false}
                        onChange={toggleSelectAll}
                        className="rounded"
                      />
                    </th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-500 w-8"></th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">产品名称</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">命名空间</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">命名空间中文名</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">指标名称</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">指标名称中文名</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">中文描述</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">单位</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-500">状态</th>
                    <th className="px-4 py-3 text-right text-sm font-medium text-gray-500">操作</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {data.items.map((metric) => (
                    <>
                      <tr key={metric.id} className="hover:bg-gray-50">
                        <td className="px-4 py-3">
                          <input
                            type="checkbox"
                            checked={selectedIds.has(metric.id)}
                            onChange={() => toggleSelect(metric.id)}
                            className="rounded"
                          />
                        </td>
                        <td className="px-4 py-3">
                          <button
                            onClick={() => setExpandedRow(expandedRow === metric.id ? null : metric.id)}
                            className="text-gray-400 hover:text-gray-600"
                          >
                            {expandedRow === metric.id ? (
                              <ChevronDown className="w-4 h-4" />
                            ) : (
                              <ChevronRight className="w-4 h-4" />
                            )}
                          </button>
                        </td>
                        <td className="px-4 py-3 text-sm font-medium text-gray-900">
                          {metric.product || '-'}
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-600 font-mono text-xs">
                          {metric.namespace || '-'}
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-600">
                          {metric.namespace_desc ? (
                            metric.namespace_desc
                          ) : (
                            <span className="text-gray-400 italic">-</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-600 font-mono">
                          {metric.metric_name || '-'}
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-600">
                          {metric.metric_name_desc ? (
                            metric.metric_name_desc
                          ) : (
                            <span className="text-gray-400 italic">-</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-600">
                          {metric.metric_desc ? (
                            metric.metric_desc
                          ) : (
                            <span className="text-gray-400 italic">未填写</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-500">
                          {metric.unit || '-'}
                        </td>
                        <td className="px-4 py-3">
                          <button
                            onClick={() =>
                              toggleActiveMutation.mutate({
                                id: metric.id,
                                is_active: metric.is_active === 1 ? 0 : 1,
                              })
                            }
                            disabled={toggleActiveMutation.isPending}
                            className={`px-2 py-1 text-xs rounded disabled:opacity-50 ${
                              metric.is_active === 1
                                ? 'bg-green-100 text-green-800'
                                : 'bg-gray-100 text-gray-800'
                            }`}
                          >
                            {metric.is_active === 1 ? '启用' : '停用'}
                          </button>
                        </td>
                        <td className="px-4 py-3 text-right">
                          <div className="flex justify-end gap-2">
                            <button
                              onClick={() => handleEdit(metric)}
                              className="text-blue-600 hover:text-blue-800 text-sm"
                            >
                              编辑
                            </button>
                            <button
                              onClick={() => {
                                if (confirm('确定要删除该指标吗？')) {
                                  deleteMutation.mutate(metric.id)
                                }
                              }}
                              disabled={deleteMutation.isPending}
                              className="text-red-600 hover:text-red-800 text-sm disabled:opacity-50"
                            >
                              删除
                            </button>
                          </div>
                        </td>
                      </tr>
                      {expandedRow === metric.id && (
                        <tr key={`${metric.id}-expanded`}>
                          <td colSpan={11} className="px-4 py-4 bg-gray-50">
                            <div className="grid grid-cols-3 gap-4 text-sm">
                              <div>
                                <div className="text-gray-500 mb-1">产品名称</div>
                                <div className="text-gray-900">{metric.product || '-'}</div>
                              </div>
                              <div>
                                <div className="text-gray-500 mb-1">命名空间</div>
                                <div className="text-gray-900 font-mono">{metric.namespace || '-'}</div>
                              </div>
                              <div>
                                <div className="text-gray-500 mb-1">命名空间中文名</div>
                                <div className="text-gray-900">{metric.namespace_desc || '-'}</div>
                              </div>
                              <div>
                                <div className="text-gray-500 mb-1">指标名称</div>
                                <div className="text-gray-900 font-mono">{metric.metric_name || '-'}</div>
                              </div>
                              <div>
                                <div className="text-gray-500 mb-1">指标名称中文名</div>
                                <div className="text-gray-900">{metric.metric_name_desc || '-'}</div>
                              </div>
                              <div>
                                <div className="text-gray-500 mb-1">中文描述</div>
                                <div className="text-gray-900">
                                  {metric.metric_desc || <span className="text-gray-400 italic">未填写</span>}
                                </div>
                              </div>
                              <div>
                                <div className="text-gray-500 mb-1">单位</div>
                                <div className="text-gray-900">{metric.unit || '-'}</div>
                              </div>
                              <div>
                                <div className="text-gray-500 mb-1">维度</div>
                                <div className="text-gray-900">
                                  {metric.dimensions?.length ? metric.dimensions.join(', ') : '-'}
                                </div>
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            <div className="p-4 border-t flex items-center justify-between">
              <div className="text-sm text-gray-500">
                共 {data.total} 条记录
                {isFetching && !isLoading && (
                  <span className="ml-2 text-blue-500">
                    <Loader2 className="w-3 h-3 animate-spin inline" /> 刷新中...
                  </span>
                )}
              </div>
              <div className="flex gap-2 items-center">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page <= 1}
                  className="px-3 py-1 border rounded text-sm disabled:opacity-40 hover:bg-gray-50"
                >
                  上一页
                </button>
                <span className="text-sm text-gray-600">
                  第 {page} / {totalPages || 1} 页
                </span>
                <button
                  onClick={() => setPage((p) => p + 1)}
                  disabled={page >= totalPages}
                  className="px-3 py-1 border rounded text-sm disabled:opacity-40 hover:bg-gray-50"
                >
                  下一页
                </button>
              </div>
            </div>
          </>
        )}
      </div>

      {/* Edit Modal */}
      {showModal && (
        <EditModal
          metric={editingMetric}
          onClose={() => setShowModal(false)}
          onSuccess={() => setShowModal(false)}
        />
      )}

      {/* Batch Delete Confirmation */}
      {showBatchDeleteConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg w-full max-w-md p-6">
            <h3 className="text-lg font-bold mb-4">确认批量删除</h3>
            <p className="text-gray-600 mb-6">
              确定要删除选中的 {selectedIds.size} 条指标吗？此操作无法撤销。
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setShowBatchDeleteConfirm(false)}
                className="px-4 py-2 border rounded-md hover:bg-gray-50"
              >
                取消
              </button>
              <button
                onClick={confirmBatchDelete}
                disabled={batchDeleteMutation.isPending}
                className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50 flex items-center gap-2"
              >
                {batchDeleteMutation.isPending && <Loader2 className="w-4 h-4 animate-spin" />}
                确认删除
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
