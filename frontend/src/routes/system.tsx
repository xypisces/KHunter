import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/system')({
  component: Usystem,
})

function Usystem() {
  return (
    <div className="page">
      <h1 className="page-title">system</h1>
      <div className="card">
        <div className="card-body">
          <p className="text-muted">页面开发中...</p>
        </div>
      </div>
    </div>
  )
}
