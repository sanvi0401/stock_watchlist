export type Severity = 'STABLE' | 'NOTABLE' | 'MEANINGFUL' | 'HIGH'
export type DataStatus = 'LIVE' | 'DELAYED' | 'STALE' | 'UNAVAILABLE'
export type MarketState = 'OPEN' | 'CLOSED' | 'PRE_MARKET' | string

export type Quote = {
  symbol: string
  company_name: string
  current_price: number
  previous_close: number
  previous_price: number | null
  baseline_at: string | null
  price_change_percent: number
  since_last_check_percent: number | null
  volume: number
  average_volume: number
  volatility: number
  market_cap: number
  week_52_high: number
  week_52_low: number
  sparkline: number[]
  timestamp: string
  source: string
  data_status: DataStatus
  market_state: MarketState
  first_seen: boolean
  significance_score: number
  severity: Severity
  explanation: string
  change_type: string
  evidence: string[]
}

export type WatchlistStock = { symbol: string; added_at: string; quote: Quote | null }

export type Watchlist = {
  id: number
  name: string
  category: string
  created_at: string
  stock_count: number
  stocks: WatchlistStock[]
  attention_count: number
  meaningful_count: number
  stable_count: number
  unavailable_count: number
}

export type Dashboard = {
  greeting: string
  baseline_at: string | null
  last_checked_at: string | null
  stocks_tracked: number
  watchlist_count: number
  meaningful_changes: number
  needs_attention: number
  stable_count: number
  market_state: MarketState
  data_status: DataStatus
  needs_attention_items: Quote[]
  meaningful_items: Quote[]
  stable_items: Quote[]
  unavailable_items: Quote[]
  first_time: boolean
  new_visit: boolean
}

export type SearchHit = {
  symbol: string
  company_name: string
  current_price: number | null
  price_change_percent: number | null
  data_status: DataStatus
  market_state: MarketState
}

export type HistoryItem = {
  id: number
  timestamp: string
  symbol: string
  change_type: string
  significance_score: number
  severity: Severity
  baseline_price: number
  current_price: number
  since_last_check_percent: number
  explanation: string
  evidence: string[]
}

export type Settings = {
  name: string
  email: string
  timezone: string
  sensitivity: 'conservative' | 'balanced' | 'sensitive' | string
  lookback_mode: 'since_last_check' | 'previous_close' | 'five_day' | string
  high_significance_only: boolean
  onboarding_complete: boolean
  created_at?: string | null
}

export type User = {
  id: number
  name: string
  email: string
  timezone: string
  onboarding_complete: boolean
  sensitivity: string
  lookback_mode: string
  created_at?: string | null
}

export type Health = {
  ok: boolean
  environment: string
  provider: string
  cache: 'redis' | 'memory'
  persistence: 'durable' | 'ephemeral'
  market_state: MarketState
  server_time: string
}

export type Notification = { id: number; title: string; body: string; kind: string; read: boolean; created_at: string }
