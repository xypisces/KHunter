"""
页面渲染路由 - 仅用于开发阶段，React 上线后可删除
"""
from typing import Any
from flask import Blueprint, render_template

views_bp = Blueprint("views", __name__)


@views_bp.route("/")
def index() -> Any:
    """主页"""
    return render_template("index.html")
