"""
Web 服务器 - A股量化选股系统前端

使用工厂模式创建应用，路由已拆分到 web/routes/ 目录
"""
from web.app_factory import create_app
from utils.log_config import get_logger

# 创建应用和 SocketIO 实例
app, socketio = create_app()

logger = get_logger(__name__)


def run_web_server(host: str = "0.0.0.0", port: int = 8080, debug: bool = False) -> None:
    """启动Web服务器"""
    from utils.log_config import LogConfig

    LogConfig.setup_logging()

    # 打印所有注册的路由
    print("\n注册的路由:")
    for rule in app.url_map.iter_rules():
        print(f"  {rule}")

    print(f"\n启动Web服务器: http://{host}:{port}")
    socketio.run(app, host=host, port=port, debug=debug, allow_unsafe_werkzeug=True)


if __name__ == "__main__":
    run_web_server()
