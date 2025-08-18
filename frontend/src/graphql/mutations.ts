import { gql } from '@apollo/client';

export const PLACE_ORDER = gql`
  mutation PlaceOrder($input: OrderInput!) {
    placeOrder(input: $input) {
      success
      orderId
      message
      order {
        orderId
        symbol
        side
        orderType
        price
        quantity
        status
        createdAt
      }
    }
  }
`;

export const CANCEL_ORDER = gql`
  mutation CancelOrder($orderId: String!) {
    cancelOrder(orderId: $orderId) {
      success
      message
    }
  }
`;

export const CLOSE_POSITION = gql`
  mutation ClosePosition($symbol: String!) {
    closePosition(symbol: $symbol) {
      success
      message
      realizedPnl
    }
  }
`;

export const UPDATE_SETTINGS = gql`
  mutation UpdateSettings($input: SettingsInput!) {
    updateSettings(input: $input) {
      success
      message
    }
  }
`;