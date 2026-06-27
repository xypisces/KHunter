#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
技术分析模块
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from indicators import ma, ema, rsi, kdj, macd, bollinger


class TechnicalAnalyzer:
    """技术分析器"""
    
    def __init__(self):
        """初始化技术分析器"""
        pass
    
    def calculate_ma(self, data: pd.DataFrame, periods: List[int]) -> pd.DataFrame:
        """计算移动平均线

        Args:
            data: 历史行情数据
            periods: 移动平均线周期列表

        Returns:
            pd.DataFrame: 添加了移动平均线的数据集
        """
        if data is None or data.empty:
            return data

        for period in periods:
            data[f'ma{period}'] = ma(data['close'], period)  # type: ignore[arg-type]
        return data
    
    def calculate_macd(self, data: pd.DataFrame, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9) -> pd.DataFrame:
        """计算MACD指标

        Args:
            data: 历史行情数据
            fast_period: 快速移动平均线周期
            slow_period: 慢速移动平均线周期
            signal_period: 信号线周期

        Returns:
            pd.DataFrame: 添加了MACD指标的数据集
        """
        if data is None or data.empty:
            return data

        # 计算MACD
        dif, dea, hist = macd(data, fast_period, slow_period, signal_period)
        data['macd'] = dif
        data['signal'] = dea
        data['hist'] = hist

        return data
    
    def calculate_rsi(self, data: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """计算RSI指标

        Args:
            data: 历史行情数据
            period: RSI周期

        Returns:
            pd.DataFrame: 添加了RSI指标的数据集
        """
        if data is None or data.empty:
            return data

        # 计算RSI
        data['rsi'] = rsi(data, period)

        return data
    
    def calculate_bollinger_bands(self, data: pd.DataFrame, period: int = 20, std_dev: float = 2) -> pd.DataFrame:
        """计算布林带

        Args:
            data: 历史行情数据
            period: 移动平均线周期
            std_dev: 标准差倍数

        Returns:
            pd.DataFrame: 添加了布林带的数据集
        """
        if data is None or data.empty:
            return data

        # 计算布林带
        mid, upper, lower = bollinger(data, period, std_dev)
        data['bb_mid'] = mid
        data['bb_upper'] = upper
        data['bb_lower'] = lower

        return data
    
    def calculate_kdj(self, data: pd.DataFrame, n: int = 9, m1: int = 3, m2: int = 3) -> pd.DataFrame:
        """计算KDJ指标

        Args:
            data: 历史行情数据
            n: 周期
            m1: K值平滑周期
            m2: D值平滑周期

        Returns:
            pd.DataFrame: 添加了KDJ指标的数据集
        """
        if data is None or data.empty:
            return data

        # 计算KDJ
        k, d, j = kdj(data, n, m1, m2)
        data['k'] = k
        data['d'] = d
        data['j'] = j

        return data
    
    def analyze_trend(self, data: pd.DataFrame) -> Dict[str, Any]:
        """分析趋势
        
        Args:
            data: 历史行情数据
            
        Returns:
            dict: 趋势分析结果
        """
        if data is None or data.empty:
            return {
                "trend": "未知",
                "strength": 0,
                "support": 0,
                "resistance": 0
            }
        
        # 计算关键指标
        data = self.calculate_ma(data, [20, 50, 200])
        data = self.calculate_macd(data)
        data = self.calculate_rsi(data)
        
        # 分析趋势
        trend = "未知"
        strength = 0
        
        # 基于MA判断趋势
        if 'ma20' in data.columns and 'ma50' in data.columns and 'ma200' in data.columns:
            latest_data = data.iloc[-1]
            
            if latest_data['ma20'] > latest_data['ma50'] > latest_data['ma200']:
                trend = "上升"
                strength = 3
            elif latest_data['ma20'] < latest_data['ma50'] < latest_data['ma200']:
                trend = "下降"
                strength = 3
            elif latest_data['ma20'] > latest_data['ma50'] < latest_data['ma200']:
                trend = "震荡"
                strength = 1
            elif latest_data['ma20'] < latest_data['ma50'] > latest_data['ma200']:
                trend = "震荡"
                strength = 1
        
        # 基于MACD判断趋势
        if 'macd' in data.columns and 'signal' in data.columns:
            latest_data = data.iloc[-1]
            if latest_data['macd'] > latest_data['signal'] and latest_data['macd'] > 0:
                trend = "上升"
                strength += 1
            elif latest_data['macd'] < latest_data['signal'] and latest_data['macd'] < 0:
                trend = "下降"
                strength += 1
        
        # 计算支撑位和阻力位
        support = data['low'].tail(20).min()
        resistance = data['high'].tail(20).max()
        
        return {
            "trend": trend,
            "strength": strength,
            "support": support,
            "resistance": resistance
        }
    
    def analyze_volatility(self, data: pd.DataFrame) -> Dict[str, Any]:
        """分析波动率
        
        Args:
            data: 历史行情数据
            
        Returns:
            dict: 波动率分析结果
        """
        if data is None or data.empty:
            return {
                "volatility": 0,
                "volatility_level": "低",
                "bb_width": 0
            }
        
        # 计算波动率
        data = self.calculate_bollinger_bands(data)
        
        # 计算历史波动率
        returns = data['close'].pct_change()
        volatility = returns.std() * np.sqrt(252)  # 年化波动率
        
        # 确定波动率水平
        volatility_level = "低"
        if volatility > 0.4:
            volatility_level = "高"
        elif volatility > 0.2:
            volatility_level = "中"
        
        # 计算布林带宽度
        bb_width = 0
        if 'bb_upper' in data.columns and 'bb_lower' in data.columns and 'bb_mid' in data.columns:
            latest_data = data.iloc[-1]
            bb_width = (latest_data['bb_upper'] - latest_data['bb_lower']) / latest_data['bb_mid'] * 100
        
        return {
            "volatility": volatility,
            "volatility_level": volatility_level,
            "bb_width": bb_width
        }
    
    def analyze_momentum(self, data: pd.DataFrame) -> Dict[str, Any]:
        """分析动量
        
        Args:
            data: 历史行情数据
            
        Returns:
            dict: 动量分析结果
        """
        if data is None or data.empty:
            return {
                "momentum": 0,
                "momentum_strength": "弱",
                "rsi_level": "中性"
            }
        
        # 计算动量指标
        data = self.calculate_rsi(data)
        
        # 计算动量
        if len(data) >= 10:
            momentum = data['close'].iloc[-1] / data['close'].iloc[-10] - 1
        else:
            momentum = 0
        
        # 确定动量强度
        momentum_strength = "弱"
        if momentum > 0.1:
            momentum_strength = "强"
        elif momentum > 0.05:
            momentum_strength = "中等"
        elif momentum < -0.1:
            momentum_strength = "强"
        elif momentum < -0.05:
            momentum_strength = "中等"
        
        # 分析RSI水平
        rsi_level = "中性"
        if 'rsi' in data.columns:
            latest_rsi = data['rsi'].iloc[-1]
            if latest_rsi > 70:
                rsi_level = "超买"
            elif latest_rsi < 30:
                rsi_level = "超卖"
        
        return {
            "momentum": momentum,
            "momentum_strength": momentum_strength,
            "rsi_level": rsi_level
        }
    
    def analyze_volume(self, data: pd.DataFrame) -> Dict[str, Any]:
        """分析成交量
        
        Args:
            data: 历史行情数据
            
        Returns:
            dict: 成交量分析结果
        """
        if data is None or data.empty:
            return {
                "volume_trend": "稳定",
                "volume_change": 0,
                "volume_ratio": 1
            }
        
        # 计算成交量趋势
        volume_trend = "稳定"
        volume_change = 0
        volume_ratio = 1
        
        if 'volume' in data.columns:
            # 计算成交量变化
            if len(data) >= 2:
                current_volume = data['volume'].iloc[-1]
                prev_volume = data['volume'].iloc[-2]
                volume_change = (current_volume - prev_volume) / prev_volume
                
                # 计算成交量比率（与5日均量比较）
                if len(data) >= 5:
                    avg_volume_5 = data['volume'].tail(5).mean()
                    volume_ratio = current_volume / avg_volume_5
                
                # 确定成交量趋势
                if volume_change > 0.2:
                    volume_trend = "增加"
                elif volume_change < -0.2:
                    volume_trend = "减少"
        
        return {
            "volume_trend": volume_trend,
            "volume_change": volume_change,
            "volume_ratio": volume_ratio
        }
    
    def comprehensive_technical_analysis(self, data: pd.DataFrame) -> Dict[str, Any]:
        """综合技术分析 - 直接返回前端期望格式

        Args:
            data: 历史行情数据

        Returns:
            dict: 前端期望格式 {trend, indicators, patterns, score, opinion}
        """
        if data is None or data.empty:
            return {
                "trend": "未知",
                "indicators": {"MACD": "未知", "KDJ": "未知", "RSI": 50.0, "Bollinger": "未知"},
                "patterns": [],
                "score": 0,
                "opinion": "数据不足"
            }

        # 计算指标
        data = self.calculate_ma(data, [5, 20])
        data = self.calculate_macd(data)
        data = self.calculate_rsi(data)
        data = self.calculate_kdj(data)
        data = self.calculate_bollinger_bands(data)

        # 趋势判断
        trend = "横盘"
        if 'ma5' in data.columns and 'ma20' in data.columns:
            latest = data.iloc[-1]
            if latest['ma5'] > latest['ma20']:
                trend = "上升趋势"
            elif latest['ma5'] < latest['ma20']:
                trend = "下降趋势"

        # MACD 状态
        macd_status = "未知"
        if 'macd' in data.columns and 'signal' in data.columns:
            latest = data.iloc[-1]
            if latest['macd'] > latest['signal'] and latest['macd'] > 0:
                macd_status = "多头"
            elif latest['macd'] < latest['signal'] and latest['macd'] < 0:
                macd_status = "空头"
            elif latest['macd'] > latest['signal']:
                macd_status = "金叉"
            else:
                macd_status = "死叉"

        # KDJ 状态
        kdj_status = "未知"
        if 'k' in data.columns and 'd' in data.columns:
            latest = data.iloc[-1]
            if latest['k'] > 80 and latest['d'] > 80:
                kdj_status = "超买"
            elif latest['k'] < 20 and latest['d'] < 20:
                kdj_status = "超卖"
            elif latest['k'] > latest['d']:
                kdj_status = "金叉"
            else:
                kdj_status = "死叉"

        # RSI 值
        rsi_value = 50.0
        if 'rsi' in data.columns:
            rsi_value = float(data['rsi'].iloc[-1])

        # 布林带状态
        bollinger_status = "正常"
        if 'bb_upper' in data.columns and 'bb_lower' in data.columns:
            latest = data.iloc[-1]
            if latest['close'] > latest['bb_upper']:
                bollinger_status = "突破上轨"
            elif latest['close'] < latest['bb_lower']:
                bollinger_status = "突破下轨"

        # 计算综合评分
        score = 50
        if trend == "上升趋势":
            score += 20
        elif trend == "下降趋势":
            score -= 20

        if macd_status in ("多头", "金叉"):
            score += 10
        elif macd_status in ("空头", "死叉"):
            score -= 10

        if kdj_status == "超卖":
            score += 10
        elif kdj_status == "超买":
            score -= 10

        if rsi_value < 30:
            score += 10
        elif rsi_value > 70:
            score -= 10

        score = max(0, min(100, score))

        # 生成意见
        opinion = "中性"
        if score >= 70:
            opinion = "看多"
        elif score <= 30:
            opinion = "看空"

        return {
            "trend": trend,
            "indicators": {
                "MACD": macd_status,
                "KDJ": kdj_status,
                "RSI": rsi_value,
                "Bollinger": bollinger_status
            },
            "patterns": [],
            "score": score,
            "opinion": opinion
        }


if __name__ == "__main__":
    # 测试技术分析器
    import sys
    from pathlib import Path

    # 添加项目根目录到路径
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from stock_analyzer.data_fetcher import StockAnalyzerDataFetcher
    import pandas as pd

    # 获取测试数据
    fetcher = StockAnalyzerDataFetcher()
    quote_dict = fetcher.get_stock_quote("600519")
    data = pd.DataFrame([quote_dict]) if quote_dict else pd.DataFrame()

    # 初始化技术分析器
    analyzer = TechnicalAnalyzer()

    # 测试综合技术分析
    result = analyzer.comprehensive_technical_analysis(data)
    print("综合技术分析结果:")
    print(f"趋势: {result['trend']}")
    print(f"指标: {result['indicators']}")
    print(f"评分: {result['score']}")
    print(f"意见: {result['opinion']}")