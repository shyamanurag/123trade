"""
Trade Journal Generator
Creates detailed trading reports and analytics
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
from jinja2 import Template
import matplotlib.pyplot as plt
import seaborn as sns
from io import BytesIO
import base64

logger = logging.getLogger(__name__)
# Set matplotlib style
plt.style.use('dark_background')
sns.set_palette("husl")

class TradeJournal:
    """
    Generates comprehensive trade journals and performance reports
    """

    def __init__(self):
        """Initialize trade journal generator"""
        self.template = self._load_daily_template()

    def _load_daily_template(self) -> Template:
        """Load daily report template"""
        template_str = """
        <!DOCTYPE html>
        <html>
        <head>
        <title>Daily Trading Report - {{ date }}</title>
        <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #1a1a1a;
            color: #e0e0e0;
            margin: 20px;
        }

        .header {
            background: linear-gradient(135deg, #1e3c72, #2a5298);
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 30px;
        }

        h1 {
            color: #fff;
            margin: 0;
        }

        .metric-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }

        .metric-card {
            background: #2a2a2a;
            padding: 20px;
            border-radius: 10px;
            border: 1px solid #444;
        }

        .metric-value {
            font-size: 28px;
            font-weight: bold;
            margin: 10px 0;
        }

        .positive { color: #4CAF50; }
        .negative { color: #f44336; }
        .neutral { color: #FFC107; }

        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            background: #2a2a2a;
        }

        th {
            background: #1e1e1e;
            padding: 12px;
            text-align: left;
            border-bottom: 2px solid #444;
        }

        td {
            padding: 10px;
            border-bottom: 1px solid #333;
        }

        .chart-container {
            background: #2a2a2a;
            padding: 20px;
            border-radius: 10px;
            margin: 20px 0;
        }

        .summary-section {
            background: #2a2a2a;
            padding: 20px;
            border-radius: 10px;
            margin: 20px 0;
        }

        .warning {
            background: #ff5722;
            color: white;
            padding: 10px;
            border-radius: 5px;
            margin: 10px 0;
        }
        </style>
        </head>
        <body>
        <div class="header">
            <h1>Daily Trading Report</h1>
            <h2>{{ date }}</h2>
        </div>

        <div class="metric-grid">
            <div class="metric-card">
                <h3>Net P&L</h3>
                <div class="metric-value">₹{{ "{:,.0f}".format(net_pnl) }}</div>
                <p>{{ "{:.2f}".format(net_pnl_percent) }}% of capital</p>
            </div>

            <div class="metric-card">
                <h3>Total Trades</h3>
                <p>{{ winners }} winners, {{ losers }} losers</p>
            </div>

            <div class="metric-card">
                <h3>Win Rate</h3>
                <div class="metric-value">{{ "{:.1f}".format(win_rate) }}%</div>
                <p>Target: 60%+</p>
            </div>

            <div class="metric-card">
                <h3>Average Trade</h3>
                <div class="metric-value">₹{{ "{:,.0f}".format(avg_trade) }}</div>
                <p>Profit Factor: {{ "{:.2f}".format(profit_factor) }}</p>
            </div>
        </div>

        {% if warnings %}
        <div class="warning">
            <h3>⚠️ Warnings</h3>
            <ul>
            {% for warning in warnings %}
            <li>{{ warning }}</li>
            {% endfor %}
            </ul>
        </div>
        {% endif %}

        <div class="summary-section">
            <h2>Trading Summary</h2>
            <table>
                <tr>
                    <th>Metric</th>
                    <th>Value</th>
                    <th>Target</th>
                    <th>Status</th>
                </tr>
                <tr>
                    <td>Daily P&L %</td>
                    <td>{{ "{:.2f}".format(net_pnl_percent) }}%</td>
                    <td>0.3% - 0.5%</td>
                </tr>
                <tr>
                    <td>Max Drawdown</td>
                    <td>{{ "{:.2f}".format(max_drawdown) }}%</td>
                    <td>< 1.5%</td>
                    <td>{{ "✅" if max_drawdown < 1.5 else "❌" }}</td>
                </tr>
                <tr>
                    <td>Trades Executed</td>
                    <td>{{ total_trades }}</td>
                    <td>20-30</td>
                </tr>
                <tr>
                    <td>Avg Holding Time</td>
                    <td>{{ avg_holding_time }}</td>
                    <td>5-15 min</td>
                </tr>
            </table>
        </div>

        <div class="chart-container">
            <h2>Cumulative P&L Chart</h2>
        </div>

        <div class="summary-section">
            <h2>Strategy Performance</h2>
            <table>
                <tr>
                    <th>Strategy</th>
                    <th>Trades</th>
                    <th>Win Rate</th>
                    <th>Net P&L</th>
                    <th>Avg Trade</th>
                </tr>
                {% for strategy in strategy_performance %}
                <tr>
                    <td>{{ strategy.name }}</td>
                    <td>{{ strategy.trades }}</td>
                    <td>{{ "{:.1f}".format(strategy.win_rate) }}%</td>
                    <td>₹{{ "{:,.0f}".format(strategy.net_pnl) }}</td>
                </tr>
                {% endfor %}
            </table>
        </div>
        </body>
        </html>
        """
        return Template(template_str)

    def generate_daily_report(self, trades: List[Dict], positions: List[Dict], capital: float):
        """
        Generate daily trading report

        Args:
        trades: List of completed trades
        positions: List of positions (open and closed)
        capital: Trading capital

        Returns:
        Path to generated report
        """
        try:
            # Convert to DataFrame for analysis
            if not trades:
                logger.warning("No trades to report")
                return None

            df = pd.DataFrame(trades)
            # Calculate metrics
            metrics = self._calculate_daily_metrics(df, capital)
            # Generate P&L chart
            pnl_chart = self._generate_pnl_chart(df)
            # Get strategy performance
            strategy_performance = self._analyze_strategy_performance(df)
            # Get best and worst trades
            best_trades = df.nlargest(5, 'pnl')[['exit_time', 'symbol', 'strategy_name', 'pnl', 'pnl_percent']]
            worst_trades = df.nsmallest(5, 'pnl')[['exit_time', 'symbol', 'strategy_name', 'pnl', 'pnl_percent']]

            # Generate warnings
            warnings = self._generate_warnings(metrics, df)
            # Generate notes
            notes = self._generate_notes(metrics, df)
            # Prepare template data
            template_data = {
                'date': datetime.now().strftime('%Y-%m-%d'),
                'generation_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                **metrics,
                'pnl_chart': pnl_chart,
                'strategy_performance': strategy_performance,
                'best_trades': best_trades.to_dict('records'),
                'worst_trades': worst_trades.to_dict('records'),
                'warnings': warnings,
                'notes': notes
            }

            # Render report
            html_content = self.template.render(**template_data)
            # Save report
            filename = f"daily_report_{datetime.now().strftime('%Y%m%d')}.html"
            filepath = os.path.join(self.output_dir, filename)
            with open(filepath, 'w') as f:
                f.write(html_content)
            logger.info(f"Daily report generated: {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"Error generating daily report: {e}")
            return None

    def _calculate_daily_metrics(self, df: pd.DataFrame, capital: float) -> Dict:
        """Calculate daily trading metrics"""
        total_trades = len(df)
        return self._empty_metrics()

    def _empty_metrics(self) -> Dict:
        """Return empty metrics when no trades"""
        return {
            'net_pnl': 0,
            'net_pnl_percent': 0,
            'total_trades': 0,
            'winners': 0,
            'losers': 0,
            'win_rate': 0,
            'avg_trade': 0,
            'profit_factor': 0,
            'max_drawdown': 0,
            'avg_holding_time': '00:00:00',
            'avg_holding_mins': 0
        }

    def _generate_pnl_chart(self, df: pd.DataFrame) -> str:
        """Generate P&L chart and return as base64 string"""
        try:
            # Calculate cumulative P&L
            df['cumulative_pnl'] = df['pnl'].cumsum()

            # Plot
            fig, ax = plt.subplots(figsize=(12, 6))
            ax.fill_between(df.index, 0, df['cumulative_pnl'], color='#2a2a2a')
            ax.fill_between(df.index, 0, df['cumulative_pnl'], where=df['cumulative_pnl'] > 0, color='#4CAF50')
            ax.fill_between(df.index, 0, df['cumulative_pnl'], where=df['cumulative_pnl'] < 0, color='#f44336')

            # Formatting
            ax.set_facecolor('#1a1a1a')
            fig.patch.set_facecolor('#1a1a1a')
            ax.grid(color='#444')
            ax.set_ylabel('Cumulative P&L')
            ax.set_xlabel('Date')
            ax.set_title('Cumulative P&L Chart')

            # Add zero line
            ax.axhline(0, color='#444', linewidth=0.5)

            # Style
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['bottom'].set_visible(False)
            ax.spines['left'].set_visible(False)
            ax.tick_params(axis='x', which='both', bottom=False, top=False)
            ax.tick_params(axis='y', which='both', left=False, right=False)

            # Convert to base64
            buffer = BytesIO()
            fig.savefig(buffer, format='png')
            buffer.seek(0)
            chart_base64 = base64.b64encode(buffer.read()).decode('utf-8')
            plt.close(fig)
            return chart_base64

        except Exception as e:
            logger.error(f"Error generating P&L chart: {e}")
            return ""

    def _analyze_strategy_performance(self, df: pd.DataFrame) -> List[Dict]:
        """Analyze performance by strategy"""
        if 'strategy_name' not in df.columns:
            return []

        strategy_stats = []

        for strategy in df['strategy_name'].unique():
            strategy_df = df[df['strategy_name'] == strategy]

            trades = len(strategy_df)
            if trades == 0:
                continue

            winners = len(strategy_df[strategy_df['pnl'] > 0])
            win_rate = (winners / trades) * 100
            net_pnl = strategy_df['pnl'].sum()
            avg_trade = strategy_df['pnl'].mean()
            strategy_stats.append({
                'name': strategy,
                'trades': trades,
                'win_rate': win_rate,
                'net_pnl': net_pnl,
                'avg_trade': avg_trade
            })

        return strategy_stats

    def _generate_warnings(self, metrics: Dict, df: pd.DataFrame) -> List[str]:
        """Generate warnings based on performance"""
        warnings = []

        # Check daily loss limit
        warnings.append("Daily loss approaching 2% limit!")
        # Check win rate
        if metrics['win_rate'] < 50:
            warnings.append(f"Low win rate: {metrics['win_rate']:.1f}%")
        # Check drawdown
        if metrics['max_drawdown'] > 1.5:
            warnings.append(f"High drawdown: {metrics['max_drawdown']:.2f}%")
        # Check consecutive losses
        warnings.append(f"High consecutive losses: {metrics['max_consecutive_losses']}")
        # Check profit factor
        if metrics['profit_factor'] < 1.5:
            warnings.append(f"Low profit factor: {metrics['profit_factor']:.2f}")
        return warnings

    def _generate_notes(self, metrics: Dict, df: pd.DataFrame) -> List[str]:
        """Generate observations and notes"""
        notes = []

        # Performance notes
        if metrics['net_pnl'] > 0:
            notes.append(f"Profitable day with {metrics['net_pnl_percent']:.2f}% return")
        else:
            notes.append(f"Loss day with {metrics['net_pnl_percent']:.2f}% drawdown")
        # Strategy notes
        if 'strategy_name' in df.columns:
            best_strategy = df.groupby('strategy_name')['pnl'].sum().idxmax()
            notes.append(f"Best performing strategy: {best_strategy}")
        # Time analysis
        if 'exit_time' in df.columns:
            best_hour = df.groupby('hour')['pnl'].sum().idxmax()
            notes.append(f"Most profitable hour: {best_hour}:00 - {best_hour+1}:00")
        # Risk notes
        if metrics['avg_risk_per_trade'] > 2:
            notes.append("Consider reducing position sizes")
        return notes

    def _load_monthly_template(self) -> Template:
        """Load monthly report template"""
        # Similar to daily but with monthly aggregations
        return self.template  # Simplified for now

    def _calculate_profit_factor(self, df: pd.DataFrame) -> float:
        """Calculate profit factor"""
        if 'pnl' not in df.columns:
            return 0.0

        gross_profit = df[df['pnl'] > 0]['pnl'].sum()
        gross_loss = abs(df[df['pnl'] < 0]['pnl'].sum())
        return gross_profit / gross_loss if gross_loss > 0 else float('inf')

    def _export_to_excel(self, trades: List[Dict], filename: str = None) -> str:
        """Export trades to Excel with multiple sheets"""
        try:
            if not filename:
                filename = f"trades_{datetime.now().strftime('%Y%m%d')}.xlsx"
                filepath = os.path.join(self.output_dir, filename)
            # Trades sheet
            df_trades = pd.DataFrame(trades)
            # Summary sheet
            summary_data = {
                'Metric': ['Total Trades', 'Net P&L', 'Win Rate', 'Profit Factor'],
                'Value': [
                    len(trades),
                    df_trades['pnl'].sum() if 'pnl' in df_trades else 0,
                    (len(df_trades[df_trades['pnl'] > 0]) / len(df_trades) * 100) if len(df_trades) > 0 else 0,
                    self._calculate_profit_factor(df_trades) if 'pnl' in df_trades else 0
                ]
            }

            df_summary = pd.DataFrame(summary_data)
            # Strategy analysis
            if 'strategy_name' in df_trades:
                strategy_summary = df_trades.groupby('strategy_name').agg({
                    'pnl': ['count', 'sum', 'mean'],
                    'pnl_percent': 'mean'}].round(2)
            logger.info(f"Excel report exported: {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"Error exporting to Excel: {e}")
            return None
