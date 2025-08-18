import { gql } from '@apollo/client';

export const GET_BALANCE = gql`
  query GetBalance {
    balance
  }
`;

export const GET_POSITIONS = gql`
  query GetPositions {
    positions {
      symbol
      side
      size
      avgPrice
      unrealizedPnl
      realizedPnl
    }
  }
`;

// Note: Orders query not available in current API
// Using recentTrades as an alternative
export const GET_RECENT_TRADES = gql`
  query GetRecentTrades {
    recentTrades {
      id
      symbol
      side
      price
      quantity
      timestamp
      status
    }
  }
`;

// Placeholder for orders - will need backend implementation
export const GET_ORDERS = gql`
  query GetOrders {
    recentTrades {
      id
      symbol
      side
      price
      quantity
      timestamp
    }
  }
`;

export const GET_TICKER = gql`
  query GetTicker($symbol: String!) {
    ticker(symbol: $symbol) {
      symbol
      price
      bid
      ask
      volume
      high24h
      low24h
      change24h
      timestamp
    }
  }
`;

export const GET_KLINES = gql`
  query GetKlines($symbol: String!, $interval: String, $limit: Int) {
    klines(symbol: $symbol, interval: $interval, limit: $limit) {
      timestamp
      open
      high
      low
      close
      volume
    }
  }
`;