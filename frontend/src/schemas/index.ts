import { z } from 'zod'

// 选股规则
export const RuleResultSchema = z.object({
  name: z.string(),
  hit: z.boolean(),
  value: z.number(),
  threshold: z.number(),
  weight: z.number(),
})

// 选股结果
export const SelectionResultSchema = z.object({
  stock_code: z.string(),
  stock_name: z.string(),
  signal: z.string(),
  score: z.number(),
  rules: z.array(RuleResultSchema),
  indicators: z.record(z.string(), z.number()),
})

// 选股响应
export const SelectionResponseSchema = z.object({
  success: z.boolean(),
  date: z.string(),
  stocks: z.array(SelectionResultSchema),
})

// 股票详情
export const StockDetailSchema = z.object({
  stock_code: z.string(),
  stock_name: z.string(),
  industry: z.string().optional(),
  sector: z.string().optional(),
})

// K 线数据
export const KlineDataSchema = z.object({
  date: z.string(),
  open: z.number(),
  high: z.number(),
  low: z.number(),
  close: z.number(),
  volume: z.number(),
})

// 回测交易记录
export const BacktestTradeSchema = z.object({
  date: z.string(),
  action: z.enum(['buy', 'sell']),
  stock_code: z.string(),
  stock_name: z.string(),
  price: z.number(),
  pnl: z.number().optional(),
  pnl_percent: z.number().optional(),
})

// 回测结果摘要
export const BacktestSummarySchema = z.object({
  total_return: z.number(),
  annual_return: z.number(),
  max_drawdown: z.number(),
  sharpe_ratio: z.number(),
  win_rate: z.number(),
  total_trades: z.number(),
  profit_loss_ratio: z.number(),
})

// WebSocket 进度事件
export const ProgressEventSchema = z.object({
  current: z.number(),
  total: z.number(),
  stock_code: z.string().optional(),
  stock_name: z.string().optional(),
  phase: z.string().optional(),
  success: z.number().optional(),
  failed: z.number().optional(),
})

// 任务完成事件
export const TaskCompletedEventSchema = z.object({
  task: z.string(),
  success: z.boolean(),
  message: z.string(),
})

// 任务错误事件
export const TaskErrorEventSchema = z.object({
  task: z.string(),
  error: z.string(),
})

// 仪表盘统计
export const DashboardStatsSchema = z.object({
  market_temperature: z.number().optional(),
  market_temperature_status: z.string().optional(),
  up_count: z.number().optional(),
  down_count: z.number().optional(),
  hot_industries: z.array(z.string()).optional(),
  data_status: z.string().optional(),
  data_last_update: z.string().optional(),
})

// 风险状态
export const RiskStatusSchema = z.object({
  status: z.enum(['normal', 'warning', 'danger']),
  continuous_high_days: z.number(),
  suggestion: z.string(),
})

// 类型导出
export type RuleResult = z.infer<typeof RuleResultSchema>
export type SelectionResult = z.infer<typeof SelectionResultSchema>
export type SelectionResponse = z.infer<typeof SelectionResponseSchema>
export type StockDetail = z.infer<typeof StockDetailSchema>
export type KlineData = z.infer<typeof KlineDataSchema>
export type BacktestTrade = z.infer<typeof BacktestTradeSchema>
export type BacktestSummary = z.infer<typeof BacktestSummarySchema>
export type ProgressEvent = z.infer<typeof ProgressEventSchema>
export type TaskCompletedEvent = z.infer<typeof TaskCompletedEventSchema>
export type TaskErrorEvent = z.infer<typeof TaskErrorEventSchema>
export type DashboardStats = z.infer<typeof DashboardStatsSchema>
export type RiskStatus = z.infer<typeof RiskStatusSchema>
