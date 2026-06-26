"""
StockRepo 单元测试

使用内存 SQLite 数据库，不依赖文件系统。
"""

import sqlite3
import pandas as pd
import pytest

from utils.db_manager import DBManager
from utils.stock_repo import StockRepo


@pytest.fixture
def db():
    """创建内存数据库 DBManager 实例"""
    manager = DBManager(db_path=":memory:")
    # 创建 stock_kline 表
    manager.execute("""
        CREATE TABLE stock_kline (
            code TEXT NOT NULL,
            date TEXT NOT NULL,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER,
            market_cap REAL,
            K REAL,
            D REAL,
            J REAL,
            PRIMARY KEY (code, date)
        )
    """)
    manager.connect().commit()
    # 创建 stock_basic 表
    manager.execute("""
        CREATE TABLE stock_basic (
            code TEXT PRIMARY KEY,
            name TEXT
        )
    """)
    manager.connect().commit()
    return manager


@pytest.fixture
def repo(db):
    """创建 StockRepo 实例"""
    return StockRepo(db)


def _insert_kline(db: DBManager, code: str, date: str, close: float = 10.0):
    """辅助：插入一条 K 线数据"""
    db.execute(
        "INSERT INTO stock_kline (code, date, open, high, low, close, volume) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (code, date, 10.0, 11.0, 9.0, close, 1000),
    )
    db.connect().commit()


def _insert_basic(db: DBManager, code: str, name: str):
    """辅助：插入一条 stock_basic 数据"""
    db.execute(
        "INSERT INTO stock_basic (code, name) VALUES (?, ?)",
        (code, name),
    )
    db.connect().commit()


class TestReadStock:
    """测试 read_stock 方法"""

    def test_read_empty(self, repo):
        """不存在的股票返回空 DataFrame"""
        df = repo.read_stock("999999")
        assert df.empty

    def test_read_basic(self, repo, db):
        """读取单只股票数据"""
        _insert_kline(db, "000001", "2025-01-01", 10.5)
        _insert_kline(db, "000001", "2025-01-02", 11.0)

        df = repo.read_stock("000001")
        assert len(df) == 2
        assert list(df.columns[:6]) == ['code', 'date', 'open', 'high', 'low', 'close']

    def test_read_with_date_range(self, repo, db):
        """按日期范围过滤"""
        _insert_kline(db, "000001", "2025-01-01", 10.0)
        _insert_kline(db, "000001", "2025-01-02", 11.0)
        _insert_kline(db, "000001", "2025-01-03", 12.0)

        df = repo.read_stock("000001", start_date="2025-01-02", end_date="2025-01-03")
        assert len(df) == 2

    def test_read_with_limit(self, repo, db):
        """限制返回行数"""
        for i in range(5):
            _insert_kline(db, "000001", f"2025-01-0{i+1}", 10.0 + i)

        df = repo.read_stock("000001", limit=3)
        assert len(df) == 3

    def test_read_order_asc(self, repo, db):
        """升序排列"""
        _insert_kline(db, "000001", "2025-01-01", 10.0)
        _insert_kline(db, "000001", "2025-01-02", 11.0)

        df = repo.read_stock("000001", order='asc')
        assert df.iloc[0]['date'] < df.iloc[1]['date']

    def test_read_date_format_with_dash(self, repo, db):
        """日期格式 YYYY-MM-DD"""
        _insert_kline(db, "000001", "2025-01-01", 10.0)
        df = repo.read_stock("000001", start_date="2025-01-01")
        assert len(df) == 1


class TestWriteStock:
    """测试 write_stock 方法"""

    def test_write_basic(self, repo, db):
        """写入基本数据"""
        df = pd.DataFrame({
            'date': ['2025-01-01', '2025-01-02'],
            'open': [10.0, 11.0],
            'high': [11.0, 12.0],
            'low': [9.0, 10.0],
            'close': [10.5, 11.5],
            'volume': [1000, 2000],
        })
        result = repo.write_stock("000001", df)
        assert result is True

        # 验证写入
        read_df = repo.read_stock("000001")
        assert len(read_df) == 2

    def test_write_empty_df(self, repo):
        """空 DataFrame 返回 False"""
        df = pd.DataFrame()
        result = repo.write_stock("000001", df)
        assert result is False

    def test_write_dedup(self, repo, db):
        """按日期去重"""
        df = pd.DataFrame({
            'date': ['2025-01-01', '2025-01-01'],
            'open': [10.0, 11.0],
            'high': [11.0, 12.0],
            'low': [9.0, 10.0],
            'close': [10.5, 11.5],
            'volume': [1000, 2000],
        })
        repo.write_stock("000001", df)

        read_df = repo.read_stock("000001")
        assert len(read_df) == 1


class TestUpdateStock:
    """测试 update_stock 方法"""

    def test_update_merge(self, repo, db):
        """增量更新合并数据"""
        # 写入初始数据
        df1 = pd.DataFrame({
            'date': ['2025-01-01'],
            'open': [10.0], 'high': [11.0], 'low': [9.0],
            'close': [10.5], 'volume': [1000],
        })
        repo.write_stock("000001", df1)

        # 增量更新
        df2 = pd.DataFrame({
            'date': ['2025-01-02'],
            'open': [11.0], 'high': [12.0], 'low': [10.0],
            'close': [11.5], 'volume': [2000],
        })
        result = repo.update_stock("000001", df2)
        assert result is True

        read_df = repo.read_stock("000001")
        assert len(read_df) == 2

    def test_update_empty(self, repo):
        """空 DataFrame 返回 False"""
        result = repo.update_stock("000001", pd.DataFrame())
        assert result is False


class TestListAllStocks:
    """测试 list_all_stocks 方法"""

    def test_empty(self, repo):
        """无数据返回空列表"""
        assert repo.list_all_stocks() == []

    def test_basic(self, repo, db):
        """返回排序后的股票列表"""
        _insert_kline(db, "000002", "2025-01-01", 10.0)
        _insert_kline(db, "000001", "2025-01-01", 10.0)

        stocks = repo.list_all_stocks()
        assert stocks == ["000001", "000002"]


class TestStockExists:
    """测试 stock_exists 方法"""

    def test_not_exists(self, repo):
        assert repo.stock_exists("999999") is False

    def test_exists(self, repo, db):
        _insert_kline(db, "000001", "2025-01-01", 10.0)
        assert repo.stock_exists("000001") is True


class TestGetStockCount:
    """测试 get_stock_count 方法"""

    def test_empty(self, repo):
        assert repo.get_stock_count() == 0

    def test_count(self, repo, db):
        _insert_kline(db, "000001", "2025-01-01", 10.0)
        _insert_kline(db, "000002", "2025-01-01", 10.0)
        assert repo.get_stock_count() == 2


class TestGetLatestTradingDate:
    """测试 get_latest_trading_date 方法"""

    def test_empty(self, repo):
        assert repo.get_latest_trading_date() is None

    def test_basic(self, repo, db):
        _insert_kline(db, "000001", "2025-01-01", 10.0)
        _insert_kline(db, "000001", "2025-01-03", 12.0)
        _insert_kline(db, "000001", "2025-01-02", 11.0)

        latest = repo.get_latest_trading_date()
        assert latest == "2025-01-03"


class TestGetStockName:
    """测试 get_stock_name 方法"""

    def test_not_found(self, repo):
        assert repo.get_stock_name("999999") == "未知"

    def test_basic(self, repo, db):
        _insert_basic(db, "000001", "平安银行")
        assert repo.get_stock_name("000001") == "平安银行"


class TestGetAllStockNames:
    """测试 get_all_stock_names 方法"""

    def test_empty(self, repo):
        assert repo.get_all_stock_names() == {}

    def test_basic(self, repo, db):
        _insert_basic(db, "000001", "平安银行")
        _insert_basic(db, "000002", "万科A")

        names = repo.get_all_stock_names()
        assert names == {"000001": "平安银行", "000002": "万科A"}
