import { useParams } from 'react-router-dom'

export function AlertDetailPage() {
  const { id } = useParams<{ id: string }>()

  return (
    <div>
      <h1 className="text-2xl font-bold">告警详情</h1>
      <p className="text-gray-600">告警ID: {id}</p>
    </div>
  )
}
