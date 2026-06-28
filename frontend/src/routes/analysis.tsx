import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/analysis')({
  component: Uanalysis,
})

function Uanalysis() {
  return (
    <div className="page">
      <h1 className="page-title">analysis</h1>
      <div className="card">
        <div className="card-body">
          <p className="text-muted">页面开发中...</p>
        </div>
      </div>
    </div>
  )
}
