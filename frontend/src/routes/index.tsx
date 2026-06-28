import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/')({
  component: Dashboard,
})

function Dashboard() {
  return (
    <div className="page">
      <h1 className="page-title">仪表盘</h1>
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-label">市场温度</div>
          <div className="stat-value">--</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">今日涨跌</div>
          <div className="stat-value">--</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">活跃板块</div>
          <div className="stat-value">--</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">数据状态</div>
          <div className="stat-value">--</div>
        </div>
      </div>
      <div className="content-grid">
        <div className="card">
          <div className="card-header">最近选股结果</div>
          <div className="card-body">
            <p className="text-muted">暂无选股记录</p>
          </div>
        </div>
        <div className="card">
          <div className="card-header">市场温度趋势</div>
          <div className="card-body">
            <p className="text-muted">暂无数据</p>
          </div>
        </div>
      </div>
    </div>
  )
}
