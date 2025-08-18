"""
Telegram Bot Monitoring and Alerts
Real-time monitoring, alerts, and notifications
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from telegram import Bot
from telegram.error import TelegramError

from .bot_config import bot_settings

logger = logging.getLogger(__name__)

class AlertType(Enum):
    PRICE = "price"
    POSITION = "position"
    FUNDING = "funding"
    VOLUME = "volume"
    VOLATILITY = "volatility"
    PNL = "pnl"
    MARGIN = "margin"
    SIGNAL = "signal"
    SYSTEM = "system"

class AlertCondition(Enum):
    ABOVE = "above"
    BELOW = "below"
    CROSSES = "crosses"
    CHANGE = "change"
    PERCENT = "percent"

@dataclass
class Alert:
    """Alert configuration"""
    id: str
    user_id: int
    type: AlertType
    symbol: str
    condition: AlertCondition
    value: float
    message: str
    created_at: datetime
    triggered_at: Optional[datetime] = None
    repeat: bool = False
    cooldown: int = 300  # seconds

@dataclass
class MonitoringMetrics:
    """System monitoring metrics"""
    positions_count: int
    total_pnl: float
    margin_usage: float
    api_latency: float
    websocket_status: bool
    last_update: datetime

class MonitoringAlerts:
    """Monitoring and alert system"""
    
    def __init__(self, bot: Bot, api_client):
        """
        Initialize monitoring system
        
        Args:
            bot: Telegram bot instance
            api_client: API client for data
        """
        self.bot = bot
        self.api_client = api_client
        self.alerts: Dict[str, Alert] = {}
        self.user_alerts: Dict[int, Set[str]] = {}
        self.monitoring_active = False
        self.metrics = MonitoringMetrics(
            positions_count=0,
            total_pnl=0.0,
            margin_usage=0.0,
            api_latency=0.0,
            websocket_status=False,
            last_update=datetime.now()
        )
        
        # Price cache for efficiency
        self.price_cache: Dict[str, float] = {}
        self.last_price_update = datetime.now()
    
    async def start_monitoring(self):
        """Start the monitoring system"""
        self.monitoring_active = True
        logger.info("Starting monitoring system")
        
        # Start monitoring tasks
        tasks = [
            asyncio.create_task(self._monitor_prices()),
            asyncio.create_task(self._monitor_positions()),
            asyncio.create_task(self._monitor_funding()),
            asyncio.create_task(self._monitor_system()),
        ]
        
        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            logger.error(f"Monitoring error: {e}")
        finally:
            self.monitoring_active = False
    
    async def stop_monitoring(self):
        """Stop the monitoring system"""
        self.monitoring_active = False
        logger.info("Stopping monitoring system")
    
    async def add_alert(
        self,
        user_id: int,
        alert_type: AlertType,
        symbol: str,
        condition: AlertCondition,
        value: float,
        message: Optional[str] = None
    ) -> str:
        """
        Add a new alert
        
        Returns:
            Alert ID
        """
        alert_id = f"alert_{datetime.now().timestamp()}"
        
        alert = Alert(
            id=alert_id,
            user_id=user_id,
            type=alert_type,
            symbol=symbol,
            condition=condition,
            value=value,
            message=message or f"{alert_type.value} alert for {symbol}",
            created_at=datetime.now()
        )
        
        self.alerts[alert_id] = alert
        
        # Track user alerts
        if user_id not in self.user_alerts:
            self.user_alerts[user_id] = set()
        self.user_alerts[user_id].add(alert_id)
        
        logger.info(f"Added alert {alert_id} for user {user_id}")
        
        return alert_id
    
    async def remove_alert(self, alert_id: str, user_id: int) -> bool:
        """Remove an alert"""
        if alert_id in self.alerts:
            alert = self.alerts[alert_id]
            
            # Check ownership
            if alert.user_id != user_id and not bot_settings.is_admin(user_id):
                return False
            
            del self.alerts[alert_id]
            self.user_alerts[alert.user_id].discard(alert_id)
            
            logger.info(f"Removed alert {alert_id}")
            return True
        
        return False
    
    async def get_user_alerts(self, user_id: int) -> List[Alert]:
        """Get all alerts for a user"""
        alert_ids = self.user_alerts.get(user_id, set())
        return [self.alerts[aid] for aid in alert_ids if aid in self.alerts]
    
    async def _monitor_prices(self):
        """Monitor price alerts"""
        while self.monitoring_active:
            try:
                # Update price cache
                await self._update_price_cache()
                
                # Check price alerts
                for alert_id, alert in list(self.alerts.items()):
                    if alert.type != AlertType.PRICE:
                        continue
                    
                    if alert.symbol not in self.price_cache:
                        continue
                    
                    current_price = self.price_cache[alert.symbol]
                    triggered = False
                    
                    if alert.condition == AlertCondition.ABOVE:
                        triggered = current_price > alert.value
                    elif alert.condition == AlertCondition.BELOW:
                        triggered = current_price < alert.value
                    elif alert.condition == AlertCondition.CROSSES:
                        # Need previous price for cross detection
                        prev_price = self._get_previous_price(alert.symbol)
                        if prev_price:
                            triggered = (
                                (prev_price < alert.value and current_price >= alert.value) or
                                (prev_price > alert.value and current_price <= alert.value)
                            )
                    
                    if triggered:
                        await self._trigger_alert(alert, current_price)
                
                await asyncio.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                logger.error(f"Price monitoring error: {e}")
                await asyncio.sleep(10)
    
    async def _monitor_positions(self):
        """Monitor position-related alerts"""
        while self.monitoring_active:
            try:
                # Get all positions
                positions = await self.api_client.get_all_positions()
                
                self.metrics.positions_count = len(positions)
                self.metrics.total_pnl = sum(p['pnl'] for p in positions)
                
                # Check position alerts
                for alert_id, alert in list(self.alerts.items()):
                    if alert.type != AlertType.POSITION:
                        continue
                    
                    # Find matching position
                    position = next((p for p in positions if p['symbol'] == alert.symbol), None)
                    if not position:
                        continue
                    
                    triggered = False
                    
                    if alert.condition == AlertCondition.PERCENT:
                        # Check P&L percentage
                        pnl_pct = position['pnl_pct']
                        if abs(pnl_pct) >= alert.value:
                            triggered = True
                    elif alert.condition == AlertCondition.ABOVE:
                        # Check P&L value
                        if position['pnl'] > alert.value:
                            triggered = True
                    elif alert.condition == AlertCondition.BELOW:
                        if position['pnl'] < alert.value:
                            triggered = True
                    
                    if triggered:
                        await self._trigger_alert(alert, position)
                
                # Check margin alerts
                await self._check_margin_alerts()
                
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"Position monitoring error: {e}")
                await asyncio.sleep(30)
    
    async def _monitor_funding(self):
        """Monitor funding rate alerts"""
        while self.monitoring_active:
            try:
                # Check funding alerts
                for alert_id, alert in list(self.alerts.items()):
                    if alert.type != AlertType.FUNDING:
                        continue
                    
                    # Get funding rate
                    funding_rate = await self.api_client.get_funding_rate(alert.symbol)
                    
                    triggered = False
                    
                    if alert.condition == AlertCondition.ABOVE:
                        triggered = funding_rate > alert.value
                    elif alert.condition == AlertCondition.BELOW:
                        triggered = funding_rate < alert.value
                    
                    if triggered:
                        await self._trigger_alert(alert, funding_rate)
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Funding monitoring error: {e}")
                await asyncio.sleep(60)
    
    async def _monitor_system(self):
        """Monitor system health"""
        while self.monitoring_active:
            try:
                # Check API latency
                start_time = datetime.now()
                await self.api_client.ping()
                self.metrics.api_latency = (datetime.now() - start_time).total_seconds() * 1000
                
                # Check WebSocket status
                self.metrics.websocket_status = await self.api_client.is_websocket_connected()
                
                self.metrics.last_update = datetime.now()
                
                # Send system alerts if needed
                if self.metrics.api_latency > 1000:  # > 1 second
                    await self._send_system_alert(
                        "⚠️ High API latency detected",
                        f"Latency: {self.metrics.api_latency:.0f}ms"
                    )
                
                if not self.metrics.websocket_status:
                    await self._send_system_alert(
                        "❌ WebSocket disconnected",
                        "Real-time data may be delayed"
                    )
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"System monitoring error: {e}")
                await asyncio.sleep(60)
    
    async def _check_margin_alerts(self):
        """Check margin-related alerts"""
        try:
            account = await self.api_client.get_account_info()
            margin_ratio = account['margin_ratio']
            
            # Critical margin level
            if margin_ratio > 80:
                await self._send_critical_alert(
                    "🚨 CRITICAL: High margin usage",
                    f"Margin usage: {margin_ratio:.1f}%\n"
                    "Risk of liquidation!"
                )
            elif margin_ratio > 60:
                await self._send_warning_alert(
                    "⚠️ WARNING: Elevated margin usage",
                    f"Margin usage: {margin_ratio:.1f}%"
                )
            
            self.metrics.margin_usage = margin_ratio
            
        except Exception as e:
            logger.error(f"Margin check error: {e}")
    
    async def _trigger_alert(self, alert: Alert, data: Any):
        """Trigger an alert"""
        try:
            # Check cooldown
            if alert.triggered_at:
                cooldown_end = alert.triggered_at + timedelta(seconds=alert.cooldown)
                if datetime.now() < cooldown_end:
                    return
            
            # Format message
            message = f"🔔 *Alert Triggered*\n\n"
            message += f"Type: {alert.type.value}\n"
            message += f"Symbol: {alert.symbol}\n"
            message += f"Condition: {alert.condition.value} {alert.value}\n"
            
            if isinstance(data, dict):
                message += f"Current: {data}\n"
            else:
                message += f"Current: {data:.4f}\n"
            
            message += f"\n{alert.message}"
            
            # Send to user
            await self.bot.send_message(
                chat_id=alert.user_id,
                text=message,
                parse_mode='Markdown'
            )
            
            # Update alert
            alert.triggered_at = datetime.now()
            
            # Remove if not repeating
            if not alert.repeat:
                await self.remove_alert(alert.id, alert.user_id)
            
            logger.info(f"Alert {alert.id} triggered")
            
        except TelegramError as e:
            logger.error(f"Failed to send alert: {e}")
        except Exception as e:
            logger.error(f"Alert trigger error: {e}")
    
    async def _send_system_alert(self, title: str, message: str):
        """Send system alert to admin"""
        if not bot_settings.config.alert_chat_id:
            return
        
        try:
            full_message = f"{title}\n\n{message}\n\nTime: {datetime.now().isoformat()}"
            
            await self.bot.send_message(
                chat_id=bot_settings.config.alert_chat_id,
                text=full_message
            )
        except Exception as e:
            logger.error(f"System alert error: {e}")
    
    async def _send_critical_alert(self, title: str, message: str):
        """Send critical alert to all admins"""
        for admin_id in bot_settings.config.admin_user_ids:
            try:
                await self.bot.send_message(
                    chat_id=admin_id,
                    text=f"{title}\n\n{message}",
                    parse_mode='Markdown'
                )
            except:
                pass
    
    async def _send_warning_alert(self, title: str, message: str):
        """Send warning alert"""
        await self._send_system_alert(title, message)
    
    async def _update_price_cache(self):
        """Update price cache for monitored symbols"""
        try:
            # Get unique symbols from alerts
            symbols = set()
            for alert in self.alerts.values():
                if alert.symbol:
                    symbols.add(alert.symbol)
            
            if not symbols:
                return
            
            # Batch get prices
            prices = await self.api_client.get_prices(list(symbols))
            
            # Store previous prices
            self.previous_prices = self.price_cache.copy()
            
            # Update cache
            self.price_cache = prices
            self.last_price_update = datetime.now()
            
        except Exception as e:
            logger.error(f"Price cache update error: {e}")
    
    def _get_previous_price(self, symbol: str) -> Optional[float]:
        """Get previous price for a symbol"""
        return getattr(self, 'previous_prices', {}).get(symbol)
    
    async def send_daily_report(self, user_id: int):
        """Send daily trading report"""
        try:
            # Get daily stats
            stats = await self.api_client.get_daily_stats(user_id)
            
            message = f"""
📊 *Daily Trading Report*
{datetime.now().strftime('%Y-%m-%d')}

*Performance*
Trades: {stats['trades_count']}
Win Rate: {stats['win_rate']:.1f}%
P&L: ${stats['total_pnl']:+,.2f}

*Best Trade*
Symbol: {stats['best_trade']['symbol']}
P&L: ${stats['best_trade']['pnl']:+,.2f}

*Worst Trade*
Symbol: {stats['worst_trade']['symbol']}
P&L: ${stats['worst_trade']['pnl']:+,.2f}

*Account Status*
Balance: ${stats['balance']:,.2f}
Open Positions: {stats['open_positions']}
Margin Used: {stats['margin_usage']:.1f}%
            """
            
            await self.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Daily report error: {e}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current monitoring metrics"""
        return {
            'positions_count': self.metrics.positions_count,
            'total_pnl': self.metrics.total_pnl,
            'margin_usage': self.metrics.margin_usage,
            'api_latency': self.metrics.api_latency,
            'websocket_status': self.metrics.websocket_status,
            'last_update': self.metrics.last_update.isoformat(),
            'active_alerts': len(self.alerts),
            'monitoring_active': self.monitoring_active
        }