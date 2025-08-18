"""
Alert System Module
Manages trading alerts and notifications
"""

import logging
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from enum import Enum
import json

logger = logging.getLogger(__name__)

class AlertPriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AlertType(Enum):
    PRICE = "price"
    POSITION = "position"
    RISK = "risk"
    PERFORMANCE = "performance"
    SYSTEM = "system"
    STRATEGY = "strategy"

class Alert:
    """Individual alert object"""
    
    def __init__(self, 
                 alert_type: AlertType,
                 priority: AlertPriority,
                 title: str,
                 message: str,
                 data: Dict[str, Any] = None):
        self.id = datetime.now().strftime("%Y%m%d%H%M%S%f")
        self.type = alert_type
        self.priority = priority
        self.title = title
        self.message = message
        self.data = data or {}
        self.timestamp = datetime.now()
        self.is_read = False
        self.is_resolved = False
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'type': self.type.value,
            'priority': self.priority.value,
            'title': self.title,
            'message': self.message,
            'data': self.data,
            'timestamp': self.timestamp.isoformat(),
            'is_read': self.is_read,
            'is_resolved': self.is_resolved
        }

class AlertSystem:
    """Comprehensive alert management system"""
    
    def __init__(self):
        self.alerts: List[Alert] = []
        self.alert_rules: List[Dict[str, Any]] = []
        self.callbacks: Dict[AlertPriority, List[Callable]] = {
            AlertPriority.LOW: [],
            AlertPriority.MEDIUM: [],
            AlertPriority.HIGH: [],
            AlertPriority.CRITICAL: []
        }
        self.max_alerts = 100  # Keep last 100 alerts
        
    def add_alert(self, alert: Alert):
        """Add new alert to the system"""
        self.alerts.append(alert)
        
        # Maintain max alerts limit
        if len(self.alerts) > self.max_alerts:
            self.alerts = self.alerts[-self.max_alerts:]
        
        # Trigger callbacks
        self._trigger_callbacks(alert)
        
        logger.info(f"Alert added: [{alert.priority.value}] {alert.title}")
    
    def _trigger_callbacks(self, alert: Alert):
        """Trigger registered callbacks for alert priority"""
        callbacks = self.callbacks.get(alert.priority, [])
        for callback in callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Error in alert callback: {e}")
    
    def register_callback(self, priority: AlertPriority, callback: Callable):
        """Register callback function for specific priority alerts"""
        self.callbacks[priority].append(callback)
    
    def check_price_alerts(self, symbol: str, current_price: float):
        """Check for price-based alerts"""
        for rule in self.alert_rules:
            if rule['type'] != 'price' or rule['symbol'] != symbol:
                continue
            
            if rule['condition'] == 'above' and current_price > rule['threshold']:
                self.add_alert(Alert(
                    AlertType.PRICE,
                    AlertPriority.MEDIUM,
                    f"{symbol} Price Alert",
                    f"{symbol} price ({current_price}) is above {rule['threshold']}",
                    {'symbol': symbol, 'price': current_price, 'threshold': rule['threshold']}
                ))
                
            elif rule['condition'] == 'below' and current_price < rule['threshold']:
                self.add_alert(Alert(
                    AlertType.PRICE,
                    AlertPriority.MEDIUM,
                    f"{symbol} Price Alert",
                    f"{symbol} price ({current_price}) is below {rule['threshold']}",
                    {'symbol': symbol, 'price': current_price, 'threshold': rule['threshold']}
                ))
    
    def check_position_alerts(self, positions: List[Dict[str, Any]]):
        """Check for position-based alerts"""
        for position in positions:
            pnl_percent = position.get('unrealizedPnlPercent', 0)
            
            # Alert for large profits
            if pnl_percent > 10:
                self.add_alert(Alert(
                    AlertType.POSITION,
                    AlertPriority.HIGH,
                    f"Large Profit on {position['symbol']}",
                    f"Position has {pnl_percent:.1f}% unrealized profit. Consider taking profits.",
                    {'position': position}
                ))
            
            # Alert for large losses
            elif pnl_percent < -5:
                self.add_alert(Alert(
                    AlertType.POSITION,
                    AlertPriority.HIGH,
                    f"Large Loss on {position['symbol']}",
                    f"Position has {pnl_percent:.1f}% unrealized loss. Review stop loss.",
                    {'position': position}
                ))
    
    def check_risk_alerts(self, risk_metrics: Dict[str, Any]):
        """Check for risk-based alerts"""
        risk_score = risk_metrics.get('risk_score', 0)
        risk_level = risk_metrics.get('risk_level', 'LOW')
        
        if risk_score > 75:
            self.add_alert(Alert(
                AlertType.RISK,
                AlertPriority.CRITICAL,
                "Critical Risk Level",
                f"Risk score is {risk_score:.1f}. Trading should be paused.",
                risk_metrics
            ))
        elif risk_score > 50:
            self.add_alert(Alert(
                AlertType.RISK,
                AlertPriority.HIGH,
                "High Risk Level",
                f"Risk score is {risk_score:.1f}. Reduce exposure.",
                risk_metrics
            ))
        
        # Check specific risk factors
        if risk_metrics.get('consecutive_losses', 0) >= 3:
            self.add_alert(Alert(
                AlertType.RISK,
                AlertPriority.HIGH,
                "Consecutive Losses",
                f"{risk_metrics['consecutive_losses']} consecutive losses detected.",
                risk_metrics
            ))
        
        if risk_metrics.get('daily_pnl_percent', 0) < -3:
            self.add_alert(Alert(
                AlertType.RISK,
                AlertPriority.HIGH,
                "Daily Loss Limit Warning",
                f"Daily loss is {risk_metrics['daily_pnl_percent']:.1f}%",
                risk_metrics
            ))
    
    def check_performance_alerts(self, performance_metrics: Dict[str, Any]):
        """Check for performance-based alerts"""
        win_rate = performance_metrics.get('win_rate', 0)
        sharpe_ratio = performance_metrics.get('sharpe_ratio', 0)
        
        if win_rate < 30 and performance_metrics.get('total_trades', 0) > 10:
            self.add_alert(Alert(
                AlertType.PERFORMANCE,
                AlertPriority.MEDIUM,
                "Low Win Rate",
                f"Win rate is {win_rate:.1f}%. Review trading strategy.",
                performance_metrics
            ))
        
        if sharpe_ratio < 0.5 and performance_metrics.get('total_trades', 0) > 20:
            self.add_alert(Alert(
                AlertType.PERFORMANCE,
                AlertPriority.MEDIUM,
                "Poor Risk-Adjusted Returns",
                f"Sharpe ratio is {sharpe_ratio:.2f}. Consider strategy adjustments.",
                performance_metrics
            ))
    
    def check_system_alerts(self, system_status: Dict[str, Any]):
        """Check for system-based alerts"""
        # Check API connectivity
        if not system_status.get('api_connected', True):
            self.add_alert(Alert(
                AlertType.SYSTEM,
                AlertPriority.CRITICAL,
                "API Connection Lost",
                "Unable to connect to Bybit API",
                system_status
            ))
        
        # Check balance changes
        balance_change = system_status.get('balance_change_percent', 0)
        if abs(balance_change) > 10:
            self.add_alert(Alert(
                AlertType.SYSTEM,
                AlertPriority.HIGH,
                "Large Balance Change",
                f"Balance changed by {balance_change:.1f}%",
                system_status
            ))
    
    def add_alert_rule(self, rule: Dict[str, Any]):
        """Add custom alert rule"""
        self.alert_rules.append(rule)
        logger.info(f"Alert rule added: {rule}")
    
    def get_active_alerts(self, 
                         unread_only: bool = False,
                         priority: AlertPriority = None,
                         alert_type: AlertType = None) -> List[Dict[str, Any]]:
        """Get filtered list of alerts"""
        alerts = self.alerts
        
        if unread_only:
            alerts = [a for a in alerts if not a.is_read]
        
        if priority:
            alerts = [a for a in alerts if a.priority == priority]
        
        if alert_type:
            alerts = [a for a in alerts if a.type == alert_type]
        
        # Sort by timestamp (newest first)
        alerts.sort(key=lambda x: x.timestamp, reverse=True)
        
        return [a.to_dict() for a in alerts]
    
    def mark_alert_read(self, alert_id: str):
        """Mark alert as read"""
        for alert in self.alerts:
            if alert.id == alert_id:
                alert.is_read = True
                break
    
    def mark_alert_resolved(self, alert_id: str):
        """Mark alert as resolved"""
        for alert in self.alerts:
            if alert.id == alert_id:
                alert.is_resolved = True
                break
    
    def clear_old_alerts(self, days: int = 7):
        """Clear alerts older than specified days"""
        cutoff = datetime.now() - timedelta(days=days)
        self.alerts = [a for a in self.alerts if a.timestamp > cutoff]
    
    def get_alert_summary(self) -> Dict[str, Any]:
        """Get summary of current alerts"""
        total = len(self.alerts)
        unread = len([a for a in self.alerts if not a.is_read])
        unresolved = len([a for a in self.alerts if not a.is_resolved])
        
        by_priority = {}
        by_type = {}
        
        for alert in self.alerts:
            # Count by priority
            priority = alert.priority.value
            by_priority[priority] = by_priority.get(priority, 0) + 1
            
            # Count by type
            alert_type = alert.type.value
            by_type[alert_type] = by_type.get(alert_type, 0) + 1
        
        # Get critical alerts
        critical_alerts = [a.to_dict() for a in self.alerts 
                          if a.priority == AlertPriority.CRITICAL and not a.is_resolved]
        
        return {
            'total_alerts': total,
            'unread_alerts': unread,
            'unresolved_alerts': unresolved,
            'by_priority': by_priority,
            'by_type': by_type,
            'critical_alerts': critical_alerts[:5],  # Top 5 critical alerts
            'last_updated': datetime.now().isoformat()
        }