"""
Confluence Amplifier Strategy
Enhances signals when multiple strategies agree
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict
import numpy as np
import asyncio

from ..models import Signal, OptionType, OrderSide
from .base import BaseStrategy

logger = logging.getLogger(__name__)

@dataclass
class ConfluenceGroup:
    """Group of signals showing confluence"""
    symbol_base: str  # e.g., "NIFTY"
    direction: OrderSide
    strategies: Set[str]
    signals: List[Signal]
    timestamp: datetime

    @property
    def confluence_level(self) -> int:
        return len(self.strategies)

    @property
    def average_quality(self) -> float:
        return np.mean([s.quality_score for s in self.signals])

    @property
    def best_signal(self) -> Signal:
        return max(self.signals, key=lambda x: x.quality_score)

class ConfluenceAmplifier(BaseStrategy):
    def __init__(self, config: Dict):
        super().__init__(config)
        self._signal_lock = asyncio.Lock()
        self.signal_buffer = []
        self.signal_timestamps = {}
        self.confluence_window_seconds = config.get('confluence_window_seconds', 60)
        self.min_strategies_for_confluence = config.get('min_strategies_for_confluence', 2)
        self.confluence_boosts = {
            2: 1.5,   # Double confluence
            3: 2.5,   # Triple confluence
            4: 3.0,   # Quad confluence
            5: 3.5    # Max confluence
        }
        self.size_multipliers = {
            2: 1.1,   # 10% larger
            3: 1.2,   # 20% larger
            4: 1.3,   # 30% larger
            5: 1.4    # 40% larger
        }
        self.confluence_performance = {
            2: {'count': 0, 'pnl': 0.0, 'win_rate': 0.0},
            3: {'count': 0, 'pnl': 0.0, 'win_rate': 0.0},
            4: {'count': 0, 'pnl': 0.0, 'win_rate': 0.0},
            5: {'count': 0, 'pnl': 0.0, 'win_rate': 0.0}
        }

    async def analyze_signals(self, signals: List[Signal]) -> List[Signal]:
        """Analyze signals for confluence patterns"""
        async with self._signal_lock:
            try:
                # Add new signals to buffer
                current_time = datetime.now()
                for signal in signals:
                    self.signal_buffer.append(signal)
                    self.signal_timestamps[id(signal)] = current_time

                # Clean old signals
                await self._clean_signal_buffer()

                # Find confluence groups
                confluence_groups = await self._find_confluence_groups()

                # Create enhanced signals
                enhanced_signals = []
                for group in confluence_groups:
                    enhanced_signal = await self._create_enhanced_signal(group)
                    if enhanced_signal:
                        enhanced_signals.append(enhanced_signal)
                        logger.info(
                            f"Confluence: {enhanced_signal.metadata['confluence_strategies']} "
                            f"on {enhanced_signal.symbol} - Score: {enhanced_signal.quality_score:.1f}"
                        )
                return enhanced_signals

            except Exception as e:
                logger.error(f"Error analyzing confluence: {e}")
                return []

    async def _clean_signal_buffer(self):
        """Remove old signals from buffer"""
        current_time = datetime.now()
        cutoff_time = current_time - timedelta(seconds=self.confluence_window_seconds)
        
        # Keep only recent signals
        self.signal_buffer = [
            s for s in self.signal_buffer
            if self.signal_timestamps.get(id(s), current_time) > cutoff_time
        ]
        
        # Clean timestamps
        keys_to_remove = []
        for key, timestamp in self.signal_timestamps.items():
            if timestamp < cutoff_time:
                keys_to_remove.append(key)
        for key in keys_to_remove:
            del self.signal_timestamps[key]

    async def _find_confluence_groups(self) -> List[ConfluenceGroup]:
        """Find groups of signals showing confluence"""
        groups = []
        processed_signals = set()
        
        # Group signals by symbol base and direction
        signal_map = defaultdict(list)
        for signal in self.signal_buffer:
            if id(signal) in processed_signals:
                continue

            # Extract symbol base and determine direction
            symbol_base = self._extract_symbol_base(signal.symbol)
            direction = OrderSide.BUY if signal.option_type == OptionType.CALL else OrderSide.SELL
            
            key = (symbol_base, direction)
            signal_map[key].append(signal)
            processed_signals.add(id(signal))

        # Create confluence groups
        for (symbol_base, direction), group_signals in signal_map.items():
            if len(group_signals) < self.min_strategies_for_confluence:
                continue

            # Get unique strategies
            strategies = set(s.strategy_name for s in group_signals)
            if len(strategies) >= self.min_strategies_for_confluence:
                groups.append(ConfluenceGroup(
                    symbol_base=symbol_base,
                    direction=direction,
                    strategies=strategies,
                    signals=group_signals,
                    timestamp=datetime.now()
                ))

        return groups

    async def _create_enhanced_signal(self, group: ConfluenceGroup) -> Optional[Signal]:
        """Create an enhanced signal from a confluence group"""
        # Get the best base signal
        best_signal = group.best_signal

        # Calculate confluence boost
        confluence_level = min(group.confluence_level, 5)  # Cap at 5
        score_boost = self.confluence_boosts.get(confluence_level, 1.0)
        size_multiplier = self.size_multipliers.get(confluence_level, 1.0)

        # Create enhanced signal
        enhanced_signal = Signal(
            symbol=best_signal.symbol,
            option_type=best_signal.option_type,
            strike=best_signal.strike,
            quality_score=best_signal.quality_score * score_boost,
            quantity=int(best_signal.quantity * size_multiplier),
            metadata={
                'original_strategy': best_signal.strategy_name,
                'confluence_strategies': list(group.strategies),
                'confluence_level': confluence_level,
                'score_boost': score_boost,
                'size_multiplier': size_multiplier,
                'average_quality': round(group.average_quality, 2),
                'signal_count': len(group.signals)
            }
        )
        return enhanced_signal

    def _extract_symbol_base(self, symbol: str) -> str:
        """Extract base symbol from option symbol"""
        for base in ['NIFTY', 'BANKNIFTY', 'FINNIFTY']:
            if base in symbol:
                return base
        return symbol

    async def generate_signals(self, market_data: Dict) -> List[Signal]:
        """
        Standard signal generation interface
        This strategy primarily works through analyze_signals()
        """
        # Confluence amplifier doesn't generate its own signals
        # It enhances signals from other strategies
        return []

    def update_performance(self, trade_result: Dict):
        """Update strategy performance metrics"""
        metadata = trade_result.get('metadata', {})
        confluence_level = metadata.get('confluence_level', 0)
        pnl = trade_result.get('pnl', 0)
        if confluence_level in self.confluence_performance:
            # Update win rate
            if pnl > 0:
                wins = self.confluence_performance[confluence_level].get('wins', 0) + 1
                self.confluence_performance[confluence_level]['win_rate'] = wins / self.confluence_performance[confluence_level]['count']

            # Track pattern success
            strategies = tuple(sorted(metadata.get('confluence_strategies', [])))
            if strategies:
                if pnl > 0:
                    self.confluence_performance[confluence_level]['wins'] = self.confluence_performance[confluence_level].get('wins', 0) + 1
                else:
                    self.confluence_performance[confluence_level]['losses'] = self.confluence_performance[confluence_level].get('losses', 0) + 1

            super().update_performance(trade_result)

    def get_strategy_metrics(self) -> Dict:
        """Get strategy-specific metrics"""
        base_metrics = super().get_strategy_metrics()
        # Calculate pattern success rates
        pattern_stats = {}
        for pattern in set(self.successful_patterns.keys()) | set(self.failed_patterns.keys()):
            successes = self.successful_patterns.get(pattern, 0)
            failures = self.failed_patterns.get(pattern, 0)
            total = successes + failures

            if total > 0:
                pattern_stats[pattern] = {
                    'total': total,
                    'success_rate': successes / total,
                    'profitable_trades': successes
                }

        # Sort patterns by success rate
        best_patterns = sorted(pattern_stats.items(), key=lambda x: x[1]['success_rate'], reverse=True)[:5]

        base_metrics.update({
            'confluence_performance': self.confluence_performance,
            'active_signals_in_buffer': len(self.signal_buffer),
            'best_patterns': dict(best_patterns),
            'total_confluence_trades': sum(stats['count'] for stats in self.confluence_performance.values())
        })

        return base_metrics

    def get_confluence_report(self) -> Dict:
        """Generate detailed confluence analysis report"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'performance_by_level': self.confluence_performance,
            'most_successful_combinations': [],
            'timing_analysis': {},
            'recommendations': []
        }

        # Analyze most successful strategy combinations
        for pattern, count in sorted(self.successful_patterns.items(), key=lambda x: x[1], reverse=True)[:10]:
            failures = self.failed_patterns.get(pattern, 0)
            total = count + failures
            success_rate = count / total if total > 0 else 0

            report['most_successful_combinations'].append({
                'strategies': list(pattern),
                'total_trades': total,
                'success_rate': round(success_rate, 3),
                'profit_factor': self._calculate_pattern_profit_factor(pattern)
            })

        # Generate recommendations
        if self.confluence_performance[3]['win_rate'] > 0.7:
            report['recommendations'].append(
                "Triple confluence showing excellent results - consider increasing allocation"
            )

        if self.confluence_performance[2]['count'] > 50 and self.confluence_performance[2]['win_rate'] < 0.5:
            report['recommendations'].append(
                "Double confluence underperforming - review signal quality thresholds"
            )

        return report

    def _calculate_pattern_profit_factor(self, pattern: Tuple[str, ...]) -> float:
        """Calculate profit factor for a specific strategy pattern"""
        # This would need integration with trade history
        # Simplified version
        successes = self.successful_patterns.get(pattern, 0)
        failures = self.failed_patterns.get(pattern, 0)
        return float('inf') if successes > 0 else 0.0
