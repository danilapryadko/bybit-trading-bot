"""
Bot API Client
Handles communication with the backend API
"""

import aiohttp
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class BotAPIClient:
    """API client for bot backend communication"""
    
    def __init__(self, base_url: str):
        """Initialize API client"""
        self.base_url = base_url
        self.session = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if not self.session:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make API request"""
        try:
            session = await self._get_session()
            url = f"{self.base_url}{endpoint}"
            
            async with session.request(method, url, **kwargs) as response:
                data = await response.json()
                
                if response.status != 200:
                    logger.error(f"API error: {response.status} - {data}")
                    return {'success': False, 'error': data.get('message', 'API error')}
                
                return {'success': True, **data}
                
        except Exception as e:
            logger.error(f"Request error: {e}")
            return {'success': False, 'error': str(e)}
    
    # Account methods
    async def get_balance(self) -> Dict[str, Any]:
        """Get account balance"""
        return await self._request('GET', '/account/balance')
    
    async def get_positions(self) -> List[Dict[str, Any]]:
        """Get open positions"""
        result = await self._request('GET', '/positions')
        return result.get('positions', []) if result.get('success') else []
    
    async def get_all_positions(self) -> List[Dict[str, Any]]:
        """Get all positions for monitoring"""
        result = await self._request('GET', '/positions/all')
        return result.get('positions', []) if result.get('success') else []
    
    async def get_open_orders(self) -> List[Dict[str, Any]]:
        """Get open orders"""
        result = await self._request('GET', '/orders/open')
        return result.get('orders', []) if result.get('success') else []
    
    async def get_account_info(self) -> Dict[str, Any]:
        """Get account information"""
        return await self._request('GET', '/account/info')
    
    async def get_account_statistics(self) -> Dict[str, Any]:
        """Get account statistics"""
        return await self._request('GET', '/account/stats')
    
    # Trading methods
    async def place_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Place a new order"""
        return await self._request('POST', '/orders/place', json=order_data)
    
    async def close_position(self, identifier: str) -> Dict[str, Any]:
        """Close a position"""
        return await self._request('POST', f'/positions/close/{identifier}')
    
    async def close_all_positions(self) -> Dict[str, Any]:
        """Close all positions"""
        return await self._request('POST', '/positions/close-all')
    
    async def set_stop_loss(
        self,
        identifier: str,
        stop_price: float,
        trailing_pct: Optional[float] = None
    ) -> Dict[str, Any]:
        """Set stop loss"""
        data = {'stop_price': stop_price}
        if trailing_pct:
            data['trailing_pct'] = trailing_pct
        return await self._request('POST', f'/positions/{identifier}/stop-loss', json=data)
    
    async def set_take_profit(self, identifier: str, tp_price: float) -> Dict[str, Any]:
        """Set take profit"""
        return await self._request(
            'POST',
            f'/positions/{identifier}/take-profit',
            json={'tp_price': tp_price}
        )
    
    # Market data methods
    async def get_price(self, symbol: str) -> Dict[str, Any]:
        """Get current price"""
        return await self._request('GET', f'/market/price/{symbol}')
    
    async def get_prices(self, symbols: List[str]) -> Dict[str, float]:
        """Get prices for multiple symbols"""
        result = await self._request('POST', '/market/prices', json={'symbols': symbols})
        return result.get('prices', {}) if result.get('success') else {}
    
    async def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """Get ticker data"""
        return await self._request('GET', f'/market/ticker/{symbol}')
    
    async def get_funding_rate(self, symbol: str) -> float:
        """Get funding rate"""
        result = await self._request('GET', f'/market/funding/{symbol}')
        return result.get('funding_rate', 0.0) if result.get('success') else 0.0
    
    # History methods
    async def get_trade_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get trade history"""
        result = await self._request('GET', f'/history/trades?limit={limit}')
        return result.get('trades', []) if result.get('success') else []
    
    async def get_pnl_summary(self) -> Dict[str, Any]:
        """Get P&L summary"""
        return await self._request('GET', '/history/pnl')
    
    async def get_daily_stats(self, user_id: int) -> Dict[str, Any]:
        """Get daily statistics"""
        return await self._request('GET', f'/stats/daily/{user_id}')
    
    # Strategy methods
    async def get_funding_opportunities(self) -> List[Dict[str, Any]]:
        """Get funding rate opportunities"""
        result = await self._request('GET', '/strategies/funding/opportunities')
        return result.get('opportunities', []) if result.get('success') else []
    
    async def get_arbitrage_opportunities(self) -> List[Dict[str, Any]]:
        """Get arbitrage opportunities"""
        result = await self._request('GET', '/strategies/arbitrage/opportunities')
        return result.get('opportunities', []) if result.get('success') else []
    
    async def get_ml_signals(self) -> List[Dict[str, Any]]:
        """Get ML trading signals"""
        result = await self._request('GET', '/ml/signals')
        return result.get('signals', []) if result.get('success') else []
    
    async def start_grid_strategy(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Start grid trading strategy"""
        return await self._request('POST', '/strategies/grid/start', json=params)
    
    async def start_dca_strategy(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Start DCA strategy"""
        return await self._request('POST', '/strategies/dca/start', json=params)
    
    async def stop_strategy(self, strategy_id: str) -> Dict[str, Any]:
        """Stop a strategy"""
        return await self._request('POST', f'/strategies/{strategy_id}/stop')
    
    async def get_strategy_status(self, strategy_id: str) -> Dict[str, Any]:
        """Get strategy status"""
        return await self._request('GET', f'/strategies/{strategy_id}/status')
    
    # System methods
    async def ping(self) -> bool:
        """Ping API"""
        result = await self._request('GET', '/ping')
        return result.get('success', False)
    
    async def is_websocket_connected(self) -> bool:
        """Check WebSocket connection"""
        result = await self._request('GET', '/ws/status')
        return result.get('connected', False)
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get system status"""
        return await self._request('GET', '/system/status')
    
    async def close(self):
        """Close API client"""
        if self.session:
            await self.session.close()
            self.session = None