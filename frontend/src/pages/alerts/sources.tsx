import { Cloud, Box, Zap, Code, ExternalLink, Server, Bell, BarChart3, CloudCog } from 'lucide-react'

interface AlertSource {
  id: string
  name: string
  description: string
  icon: React.ElementType
  接入方式: string
  配置说明: string[]
  webhookUrl: string
}

const alertSources: AlertSource[] = [
  {
    id: 'prometheus',
    name: 'Prometheus / Alertmanager',
    description: '适用于 Prometheus + Alertmanager 架构的告警接入',
    icon: Server,
    接入方式: 'Webhook',
    配置说明: [
      '在 Alertmanager 配置文件中添加 webhook',
      '设置接收地址为平台的 Webhook URL',
    ],
    webhookUrl: '/api/v1/alerts/webhook/prometheus',
  },
  {
    id: 'grafana',
    name: 'Grafana',
    description: '接入 Grafana 告警，支持 Grafana 8.x 及以上版本的告警通道',
    icon: BarChart3,
    接入方式: 'Webhook',
    配置说明: [
      '在 Grafana 中创建 Notification channel',
      '选择 Webhook 类型',
      '填入平台的 Webhook URL',
    ],
    webhookUrl: '/api/v1/alerts/webhook/grafana',
  },
  {
    id: 'aliyun',
    name: '阿里云云监控',
    description: '接入阿里云云监控告警，支持阈值报警和事件报警，通过自定义 Webhook 回调',
    icon: Cloud,
    接入方式: 'Webhook',
    配置说明: [
      '登录云监控2.0控制台 → 告警中心 → 通知管理 → 通知对象',
      '新建 Webhook，填入平台的回调地址',
      '设置请求方法为 POST，数据格式为 JSON',
      '可选配置 Headers（如需要鉴权）',
    ],
    webhookUrl: '/api/v1/alerts/webhook/aliyun',
  },
  {
    id: 'tencent',
    name: '腾讯云',
    description: '接入腾讯云云监控告警，支持多种告警类型',
    icon: Cloud,
    接入方式: 'Webhook',
    配置说明: [
      '登录腾讯云控制台',
      '创建告警策略，选择 Webhook 回调',
      '填入平台的 Webhook 地址',
    ],
    webhookUrl: '/api/v1/alerts/webhook/tencent',
  },
  {
    id: 'huawei',
    name: '华为云云监控',
    description: '接入华为云云监控告警，支持阈值报警和事件告警',
    icon: CloudCog,
    接入方式: 'Webhook',
    配置说明: [
      '登录华为云云监控控制台',
      '创建主题并设置 HTTP 订阅',
      '填入平台的 Webhook 地址',
    ],
    webhookUrl: '/api/v1/alerts/webhook/huawei',
  },
  {
    id: 'zabbix',
    name: 'Zabbix',
    description: '适用于 Zabbix 监控系统的告警接入',
    icon: Box,
    接入方式: 'Webhook',
    配置说明: [
      '在 Zabbix 中配置 Media type',
      '选择 Webhook 类型',
      '填入平台的 Webhook URL',
    ],
    webhookUrl: '/api/v1/alerts/webhook/zabbix',
  },
  {
    id: 'custom',
    name: '自定义',
    description: '通过 Webhook API 接入任意数据源的告警',
    icon: Code,
    接入方式: 'Webhook API',
    配置说明: [
      '使用 POST 方法发送告警',
      '请求体为 JSON 格式',
      '包含必要字段：title, message, severity, labels',
    ],
    webhookUrl: '/api/v1/alerts',
  },
]

export function AlertSourcesPage() {
  return (
    <div className="p-6">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">告警提供商</h1>
        <p className="text-gray-500 mt-1">配置和管理告警接入渠道</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {alertSources.map((source) => {
          const Icon = source.icon
          return (
            <div
              key={source.id}
              className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden hover:shadow-md transition-shadow flex flex-col"
            >
              <div className="p-6 flex-1">
                <div className="flex items-start justify-between mb-4">
                  <div className="p-2 bg-blue-50 rounded-lg">
                    <Icon className="w-6 h-6 text-blue-600" />
                  </div>
                  <span className="px-2 py-1 text-xs font-medium bg-green-100 text-green-800 rounded">
                    {source.接入方式}
                  </span>
                </div>

                <h3 className="text-lg font-semibold text-gray-900 mb-2">
                  {source.name}
                </h3>
                <p className="text-sm text-gray-500 mb-4">
                  {source.description}
                </p>

                <div className="space-y-2 mb-4">
                  <div className="text-xs font-medium text-gray-700">配置步骤：</div>
                  {source.配置说明.map((step, idx) => (
                    <div key={idx} className="flex gap-2 text-sm text-gray-600">
                      <span className="text-blue-500">{idx + 1}.</span>
                      <span>{step}</span>
                    </div>
                  ))}
                </div>

                <div className="pt-4 border-t border-gray-100">
                  <div className="text-xs text-gray-500 mb-2">Webhook 地址：</div>
                  <code className="block text-xs bg-gray-50 px-3 py-2 rounded font-mono text-gray-700 break-all">
                    {source.webhookUrl}
                  </code>
                </div>
              </div>

              <div className="px-6 py-3 bg-gray-50 border-t border-gray-100 shrink-0">
                <button className="w-full flex items-center justify-center gap-2 text-sm font-medium text-blue-600 hover:text-blue-700">
                  查看配置文档
                  <ExternalLink className="w-4 h-4" />
                </button>
              </div>
            </div>
          )
        })}
      </div>

      {/* 接入统计 */}
      <div className="mt-8 p-6 bg-white rounded-xl shadow-sm border border-gray-100">
        <h3 className="text-lg font-semibold mb-4">接入统计</h3>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <div className="p-4 bg-gray-50 rounded-lg text-center">
            <div className="text-2xl font-bold text-gray-900">0</div>
            <div className="text-sm text-gray-500">已配置来源</div>
          </div>
          <div className="p-4 bg-gray-50 rounded-lg text-center">
            <div className="text-2xl font-bold text-green-600">0</div>
            <div className="text-sm text-gray-500">活跃连接</div>
          </div>
          <div className="p-4 bg-gray-50 rounded-lg text-center">
            <div className="text-2xl font-bold text-blue-600">0</div>
            <div className="text-sm text-gray-500">今日告警</div>
          </div>
          <div className="p-4 bg-gray-50 rounded-lg text-center">
            <div className="text-2xl font-bold text-yellow-600">0</div>
            <div className="text-sm text-gray-500">待处理</div>
          </div>
          <div className="p-4 bg-gray-50 rounded-lg text-center">
            <div className="text-2xl font-bold text-red-600">0</div>
            <div className="text-sm text-gray-500">严重告警</div>
          </div>
        </div>
      </div>

      {/* 快速开始 */}
      <div className="mt-6 p-6 bg-blue-50 rounded-xl border border-blue-100">
        <div className="flex items-start gap-4">
          <div className="p-2 bg-blue-100 rounded-lg">
            <Zap className="w-6 h-6 text-blue-600" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-blue-900 mb-2">快速开始</h3>
            <p className="text-sm text-blue-700 mb-4">
              选择一个告警提供商，按照配置步骤完成接入。配置完成后，告警数据将自动同步到平台。
            </p>
            <button className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium">
              查看接入文档
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}