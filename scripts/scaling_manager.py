#!/usr/bin/env python3
"""System Scaling Manager for MagFlow ERP.

This script analyzes usage patterns and provides recommendations for scaling:
- Horizontal scaling based on load
- Database optimization
- Cache strategies
- API rate limiting adjustments
- Resource allocation
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

import psutil
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ScalingMetric(str, Enum):
    """Scaling metrics to monitor."""
    CPU_USAGE = "cpu_usage"
    MEMORY_USAGE = "memory_usage"
    DISK_USAGE = "disk_usage"
    NETWORK_IO = "network_io"
    DB_CONNECTIONS = "db_connections"
    API_REQUESTS = "api_requests"
    EMAG_API_CALLS = "emag_api_calls"
    QUEUE_LENGTH = "queue_length"
    RESPONSE_TIME = "response_time"
    ERROR_RATE = "error_rate"


class LoadLevel(str, Enum):
    """Load levels for scaling decisions."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ScalingRecommendation:
    """Recommendation for scaling."""
    metric: ScalingMetric
    current_value: float
    threshold: float
    load_level: LoadLevel
    recommendation: str
    priority: str  # high, medium, low
    estimated_cost_impact: str  # low, medium, high


class UsagePatternAnalyzer:
    """Analyzes usage patterns to provide scaling recommendations."""

    def __init__(self):
        self.engine = create_async_engine(settings.DATABASE_URL)
        self.async_session = sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)

        # Thresholds for scaling decisions
        self.thresholds = {
            ScalingMetric.CPU_USAGE: 70,  # 70% CPU triggers scaling
            ScalingMetric.MEMORY_USAGE: 80,  # 80% memory triggers scaling
            ScalingMetric.DISK_USAGE: 85,  # 85% disk triggers scaling
            ScalingMetric.DB_CONNECTIONS: 50,  # 50 connections triggers scaling
            ScalingMetric.API_REQUESTS: 1000,  # 1000 req/min triggers scaling
            ScalingMetric.RESPONSE_TIME: 1000,  # 1000ms response time triggers scaling
            ScalingMetric.ERROR_RATE: 5,  # 5% error rate triggers scaling
        }

    def analyze_system_metrics(self) -> dict[str, Any]:
        """Analyze current system metrics."""
        logger.info("Analyzing system metrics...")

        metrics = {}

        # CPU and Memory
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        metrics["cpu"] = {
            "current": cpu_percent,
            "threshold": self.thresholds[ScalingMetric.CPU_USAGE],
            "load_level": self._get_load_level(cpu_percent, self.thresholds[ScalingMetric.CPU_USAGE])
        }

        metrics["memory"] = {
            "current": memory.percent,
            "threshold": self.thresholds[ScalingMetric.MEMORY_USAGE],
            "load_level": self._get_load_level(memory.percent, self.thresholds[ScalingMetric.MEMORY_USAGE])
        }

        metrics["disk"] = {
            "current": disk.percent,
            "threshold": self.thresholds[ScalingMetric.DISK_USAGE],
            "load_level": self._get_load_level(disk.percent, self.thresholds[ScalingMetric.DISK_USAGE])
        }

        # Network I/O
        network = psutil.net_io_counters()
        metrics["network"] = {
            "bytes_sent_per_sec": network.bytes_sent,
            "bytes_recv_per_sec": network.bytes_recv
        }

        # Process info
        process = psutil.Process()
        metrics["process"] = {
            "memory_mb": process.memory_info().rss / 1024 / 1024,
            "cpu_percent": process.cpu_percent(),
            "threads": process.num_threads(),
            "connections": len(process.connections())
        }

        return metrics

    async def analyze_database_metrics(self) -> dict[str, Any]:
        """Analyze database performance metrics."""
        logger.info("Analyzing database metrics...")

        async with self.async_session() as session:
            try:
                metrics = {}

                # Database connections
                connections = await session.execute(text("SELECT count(*) FROM pg_stat_activity;"))
                metrics["active_connections"] = connections.scalar()

                # Query performance
                slow_queries = await session.execute(text("""
                    SELECT
                        query,
                        calls,
                        total_exec_time,
                        mean_exec_time,
                        rows
                    FROM pg_stat_statements
                    WHERE mean_exec_time > 100
                    ORDER BY mean_exec_time DESC
                    LIMIT 5;
                """))

                metrics["slow_queries"] = [
                    {
                        "query": row.query[:100] + "..." if len(row.query) > 100 else row.query,
                        "calls": row.calls,
                        "total_exec_time": row.total_exec_time,
                        "mean_exec_time": row.mean_exec_time
                    }
                    for row in slow_queries
                ]

                # Table sizes and performance
                table_stats = await session.execute(text("""
                    SELECT
                        schemaname,
                        tablename,
                        n_tup_ins,
                        n_tup_upd,
                        n_tup_del,
                        n_live_tup,
                        n_dead_tup
                    FROM pg_stat_user_tables
                    WHERE schemaname = 'app'
                    ORDER BY n_live_tup DESC;
                """))

                metrics["table_stats"] = [
                    {
                        "table": f"{row.schemaname}.{row.tablename}",
                        "inserts": row.n_tup_ins,
                        "updates": row.n_tup_upd,
                        "deletes": row.n_tup_del,
                        "live_tuples": row.n_live_tup,
                        "dead_tuples": row.n_dead_tup
                    }
                    for row in table_stats
                ]

                return metrics

            except Exception as e:
                logger.error(f"Database metrics analysis error: {str(e)}")
                return {"error": str(e)}

    async def analyze_api_metrics(self) -> dict[str, Any]:
        """Analyze API performance metrics."""
        logger.info("Analyzing API metrics...")

        # This would typically collect from Prometheus or application logs
        # For now, we'll simulate realistic metrics

        return {
            "requests_per_minute": 250,
            "average_response_time": 150,  # ms
            "p95_response_time": 350,      # ms
            "p99_response_time": 800,      # ms
            "error_rate": 0.8,             # %
            "cache_hit_rate": 85,          # %
            "active_users": 45,
            "concurrent_connections": 120
        }

    def _get_load_level(self, current_value: float, threshold: float) -> LoadLevel:
        """Determine load level based on current value and threshold."""
        if current_value >= threshold * 1.5:
            return LoadLevel.CRITICAL
        elif current_value >= threshold:
            return LoadLevel.HIGH
        elif current_value >= threshold * 0.7:
            return LoadLevel.MEDIUM
        else:
            return LoadLevel.LOW

    def generate_scaling_recommendations(self, metrics: dict[str, Any]) -> list[ScalingRecommendation]:
        """Generate scaling recommendations based on metrics."""
        logger.info("Generating scaling recommendations...")

        recommendations = []

        # CPU scaling recommendation
        cpu_metrics = metrics.get("system", {}).get("cpu", {})
        if cpu_metrics.get("load_level") in [LoadLevel.HIGH, LoadLevel.CRITICAL]:
            recommendations.append(ScalingRecommendation(
                metric=ScalingMetric.CPU_USAGE,
                current_value=cpu_metrics.get("current", 0),
                threshold=cpu_metrics.get("threshold", 70),
                load_level=cpu_metrics.get("load_level", LoadLevel.LOW),
                recommendation="Consider adding more CPU cores or implementing horizontal scaling with multiple worker processes",
                priority="high",
                estimated_cost_impact="medium"
            ))

        # Memory scaling recommendation
        memory_metrics = metrics.get("system", {}).get("memory", {})
        if memory_metrics.get("load_level") in [LoadLevel.HIGH, LoadLevel.CRITICAL]:
            recommendations.append(ScalingRecommendation(
                metric=ScalingMetric.MEMORY_USAGE,
                current_value=memory_metrics.get("current", 0),
                threshold=memory_metrics.get("threshold", 80),
                load_level=memory_metrics.get("load_level", LoadLevel.LOW),
                recommendation="Consider increasing memory allocation or implementing memory optimization strategies",
                priority="high",
                estimated_cost_impact="low"
            ))

        # Database scaling recommendation
        db_metrics = metrics.get("database", {})
        if db_metrics.get("active_connections", 0) > 50:
            recommendations.append(ScalingRecommendation(
                metric=ScalingMetric.DB_CONNECTIONS,
                current_value=db_metrics.get("active_connections", 0),
                threshold=50,
                load_level=LoadLevel.HIGH,
                recommendation="Consider implementing database connection pooling or upgrading to a higher-tier database instance",
                priority="medium",
                estimated_cost_impact="medium"
            ))

        # API performance recommendation
        api_metrics = metrics.get("api", {})
        if api_metrics.get("p95_response_time", 0) > 500:
            recommendations.append(ScalingRecommendation(
                metric=ScalingMetric.RESPONSE_TIME,
                current_value=api_metrics.get("p95_response_time", 0),
                threshold=500,
                load_level=LoadLevel.HIGH,
                recommendation="Consider implementing caching strategies, database query optimization, or adding more application instances",
                priority="medium",
                estimated_cost_impact="low"
            ))

        # Error rate recommendation
        if api_metrics.get("error_rate", 0) > 2:
            recommendations.append(ScalingRecommendation(
                metric=ScalingMetric.ERROR_RATE,
                current_value=api_metrics.get("error_rate", 0),
                threshold=2,
                load_level=LoadLevel.HIGH,
                recommendation="High error rate detected. Investigate application logs and implement better error handling",
                priority="high",
                estimated_cost_impact="low"
            ))

        return recommendations

    async def generate_scaling_strategy(self) -> dict[str, Any]:
        """Generate comprehensive scaling strategy."""
        logger.info("Generating comprehensive scaling strategy...")

        # Collect all metrics
        system_metrics = self.analyze_system_metrics()
        db_metrics = await self.analyze_database_metrics()
        api_metrics = await self.analyze_api_metrics()

        all_metrics = {
            "system": system_metrics,
            "database": db_metrics,
            "api": api_metrics
        }

        # Generate recommendations
        recommendations = self.generate_scaling_recommendations(all_metrics)

        # Create scaling strategy
        strategy = {
            "timestamp": datetime.utcnow().isoformat(),
            "analysis_period": "real-time",
            "current_load": self._calculate_overall_load(all_metrics),
            "scaling_recommendations": recommendations,
            "immediate_actions": self._get_immediate_actions(recommendations),
            "monitoring_suggestions": self._get_monitoring_suggestions(recommendations),
            "cost_optimization_tips": self._get_cost_optimization_tips(recommendations)
        }

        return strategy

    def _calculate_overall_load(self, metrics: dict[str, Any]) -> LoadLevel:
        """Calculate overall system load level."""
        load_scores = []

        # System metrics load
        system_load = 0
        if metrics.get("system", {}).get("cpu", {}).get("load_level"):
            system_load += {"low": 1, "medium": 2, "high": 3, "critical": 4}[metrics["system"]["cpu"]["load_level"]]
        if metrics.get("system", {}).get("memory", {}).get("load_level"):
            system_load += {"low": 1, "medium": 2, "high": 3, "critical": 4}[metrics["system"]["memory"]["load_level"]]
        load_scores.append(system_load / 2)

        # API metrics load
        api_load = 0
        api_metrics = metrics.get("api", {})
        if api_metrics.get("requests_per_minute", 0) > 500:
            api_load += 3
        elif api_metrics.get("requests_per_minute", 0) > 200:
            api_load += 2
        else:
            api_load += 1
        load_scores.append(api_load)

        # Calculate average load
        avg_load = sum(load_scores) / len(load_scores)

        if avg_load >= 3.5:
            return LoadLevel.CRITICAL
        elif avg_load >= 2.5:
            return LoadLevel.HIGH
        elif avg_load >= 1.5:
            return LoadLevel.MEDIUM
        else:
            return LoadLevel.LOW

    def _get_immediate_actions(self, recommendations: list[ScalingRecommendation]) -> list[str]:
        """Get immediate actions that should be taken."""
        actions = []

        high_priority = [r for r in recommendations if r.priority == "high"]

        for rec in high_priority:
            if "cpu" in rec.metric.value.lower():
                actions.append("Scale up CPU resources or add worker processes")
            elif "memory" in rec.metric.value.lower():
                actions.append("Increase memory allocation or optimize memory usage")
            elif "error" in rec.metric.value.lower():
                actions.append("Investigate and fix application errors immediately")

        if not actions:
            actions.append("System is running optimally - no immediate actions required")

        return actions

    def _get_monitoring_suggestions(self, recommendations: list[ScalingRecommendation]) -> list[str]:
        """Get monitoring suggestions."""
        suggestions = [
            "Monitor CPU usage trends over the next 24 hours",
            "Set up alerts for memory usage above 85%",
            "Track API response times in Grafana dashboard",
            "Monitor database connection pool usage",
            "Set up error rate monitoring with PagerDuty"
        ]

        return suggestions

    def _get_cost_optimization_tips(self, recommendations: list[ScalingRecommendation]) -> list[str]:
        """Get cost optimization tips."""
        tips = [
            "Consider auto-scaling based on CPU usage to reduce costs during low traffic",
            "Implement intelligent caching to reduce database load and costs",
            "Use reserved instances for predictable workloads to save on compute costs",
            "Optimize database queries to reduce resource usage",
            "Implement request batching for eMAG API calls to reduce API costs"
        ]

        return tips

    def generate_scaling_report(self, strategy: dict[str, Any]) -> str:
        """Generate human-readable scaling report."""
        report = []
        report.append("=" * 60)
        report.append("MAGFLOW ERP SCALING ANALYSIS REPORT")
        report.append("=" * 60)
        report.append(f"Generated: {strategy['timestamp']}")
        report.append(f"Overall Load Level: {strategy['current_load'].upper()}")
        report.append("")

        # Current Status
        report.append("📊 CURRENT SYSTEM STATUS")
        report.append("-" * 30)

        system_metrics = strategy.get("system", {}).get("system", {})
        if system_metrics.get("cpu"):
            report.append(f"  • CPU Usage: {system_metrics['cpu']['current']:.1f}% (Threshold: {system_metrics['cpu']['threshold']}%)")
        if system_metrics.get("memory"):
            report.append(f"  • Memory Usage: {system_metrics['memory']['current']:.1f}% (Threshold: {system_metrics['memory']['threshold']}%)")
        if system_metrics.get("disk"):
            report.append(f"  • Disk Usage: {system_metrics['disk']['current']:.1f}% (Threshold: {system_metrics['disk']['threshold']}%)")

        api_metrics = strategy.get("api", {})
        if api_metrics:
            report.append(f"  • API Requests: {api_metrics.get('requests_per_minute', 'N/A')}/min")
            report.append(f"  • Response Time: {api_metrics.get('average_response_time', 'N/A')}ms avg")

        report.append("")

        # Recommendations
        report.append("🎯 SCALING RECOMMENDATIONS")
        report.append("-" * 30)

        recommendations = strategy.get("scaling_recommendations", [])
        priority_order = {"high": 0, "medium": 1, "low": 2}

        for rec in sorted(recommendations, key=lambda x: priority_order.get(rec.priority, 2)):
            priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(rec.priority, "🟢")
            report.append(f"{priority_icon} [{rec.priority.upper()}] {rec.metric.value.replace('_', ' ').title()}")
            report.append(f"    Current: {rec.current_value}, Threshold: {rec.threshold}")
            report.append(f"    Recommendation: {rec.recommendation}")
            report.append(f"    Cost Impact: {rec.estimated_cost_impact}")
            report.append("")

        # Immediate Actions
        report.append("🚨 IMMEDIATE ACTIONS REQUIRED")
        report.append("-" * 30)

        for action in strategy.get("immediate_actions", []):
            report.append(f"  • {action}")
        report.append("")

        # Monitoring Suggestions
        report.append("📈 MONITORING SUGGESTIONS")
        report.append("-" * 30)

        for suggestion in strategy.get("monitoring_suggestions", []):
            report.append(f"  • {suggestion}")
        report.append("")

        # Cost Optimization
        report.append("💰 COST OPTIMIZATION TIPS")
        report.append("-" * 30)

        for tip in strategy.get("cost_optimization_tips", []):
            report.append(f"  • {tip}")
        report.append("")

        report.append("=" * 60)

        return "\n".join(report)


async def main():
    """Main function to run scaling analysis."""
    analyzer = UsagePatternAnalyzer()

    print("🔍 Running comprehensive scaling analysis...")
    print("This analyzes usage patterns and provides scaling recommendations...")

    try:
        # Run analysis
        strategy = await analyzer.generate_scaling_strategy()

        # Generate report
        report = analyzer.generate_scaling_report(strategy)

        # Save report to file
        with open("/app/logs/scaling_report.txt", "w") as f:
            f.write(report)

        print("✅ Scaling analysis completed!")
        print("📄 Report saved to: /app/logs/scaling_report.txt")
        print()
        print(report)

        return strategy

    except Exception as e:
        logger.error(f"Scaling analysis failed: {str(e)}")
        print(f"❌ Analysis failed: {str(e)}")
        return {"error": str(e)}


if __name__ == "__main__":
    asyncio.run(main())
