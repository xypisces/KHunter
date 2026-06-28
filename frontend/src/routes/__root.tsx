import { createRootRoute, Outlet, Link, useRouterState } from '@tanstack/react-router'

const NAV_GROUPS = [
  {
    label: '数据',
    items: [
      { to: '/', label: '仪表盘', icon: '📊' },
      { to: '/stocks', label: '股票列表', icon: '📈' },
      { to: '/selection', label: '选股', icon: '🔍' },
      { to: '/selection-history', label: '选股历史', icon: '📋' },
    ],
  },
  {
    label: '分析',
    items: [
      { to: '/analysis', label: '个股分析', icon: '🔬' },
      { to: '/strategies', label: '策略管理', icon: '⚙️' },
      { to: '/backtest', label: '回测', icon: '🧪' },
    ],
  },
  {
    label: '运营',
    items: [
      { to: '/khunter', label: '狩猎场', icon: '🎯' },
      { to: '/risk', label: '风险监控', icon: '🛡️' },
      { to: '/system', label: '系统管理', icon: '🔧' },
    ],
  },
]

function Sidebar() {
  const routerState = useRouterState()
  const currentPath = routerState.location.pathname

  return (
    <aside className="sidebar">
      <div className="logo">
        <span className="icon">🎯</span>
        <span className="title">KHunter</span>
      </div>
      <nav className="nav-menu">
        {NAV_GROUPS.map((group) => (
          <div key={group.label} className="nav-group">
            <div className="nav-group-label">{group.label}</div>
            {group.items.map((item) => (
              <Link
                key={item.to}
                to={item.to}
                className={`nav-item ${currentPath === item.to ? 'active' : ''}`}
              >
                <span className="nav-icon">{item.icon}</span>
                <span className="nav-label">{item.label}</span>
              </Link>
            ))}
          </div>
        ))}
      </nav>
    </aside>
  )
}

function RootLayout() {
  return (
    <div className="container">
      <Sidebar />
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  )
}

export const Route = createRootRoute({
  component: RootLayout,
})
