import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/risk')({
  component: Urisk,
})

function Urisk() {
  return (
    <div className="page">
      <h1 className="page-title">risk</h1>
      <div className="card">
        <div className="card-body">
          <p className="text-muted">页面开发中...</p>
        </div>
      </div>
    </div>
  )
}
