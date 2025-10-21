"""Advanced reporting service for MagFlow ERP using dependency injection."""

import json
import logging
import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import and_, func, select

from app.core.dependency_injection import ServiceBase, ServiceContext
from app.core.service_registry import (
    get_audit_log_repository,
    get_order_repository,
    get_product_repository,
    get_user_repository,
)  # get_order_repository
from app.db.models import AuditLog, Category, Product, Role, User  # , Order

logger = logging.getLogger(__name__)


class ReportingService(ServiceBase):
    """Service for advanced reporting and analytics using dependency injection."""

    def __init__(self, context: ServiceContext):
        """Initialize reporting service with dependency injection.

        The service attempts to retrieve repositories via the global ServiceRegistry.
        In unit test environments the registry may not be initialized,
        which would raise a RuntimeError.
        To make the service usable in such contexts, we gracefully handle the error
        and set the repository attributes to ``None``.
        Tests that require a repository can patch the ``get_user_repository``
        function before instantiation.
        """
        super().__init__(context)
        try:
            self.user_repository = get_user_repository()
        except RuntimeError:
            # ServiceRegistry not initialized; repository will be None.
            self.user_repository = None
        try:
            self.product_repository = get_product_repository()
        except RuntimeError:
            self.product_repository = None
        try:
            self.order_repository = get_order_repository()
        except RuntimeError:
            self.order_repository = None
        try:
            self.audit_log_repository = get_audit_log_repository()
        except RuntimeError:
            self.audit_log_repository = None

    async def initialize(self):
        """Initialize reporting service."""
        self.logger.info("Reporting service initialized")

    async def cleanup(self):
        """Cleanup reporting service."""
        self.logger.info("Reporting service cleaned up")

    async def _generate_inventory_status(
        self,
        filters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Generate inventory status report."""
        try:
            date_range = self._get_date_range(filters)

            # Mock inventory data
            total_products = 500
            low_stock_items = 25
            out_of_stock_items = 5
            inventory_value = 250000.00

            # Mock stock movements
            stock_movements = []
            for i in range(20):
                stock_movements.append(
                    {
                        "date": (datetime.now(UTC) - timedelta(days=i)).strftime(
                            "%Y-%m-%d",
                        ),
                        "product": f"Product {chr(65 + i % 10)}",
                        "movement_type": ["in", "out", "adjustment"][i % 3],
                        "quantity": 10 + i * 2,
                        "reason": "Sale" if i % 2 == 0 else "Purchase",
                    },
                )

            # Mock category breakdown
            category_breakdown = [
                {"category": "Electronics", "items": 150, "value": 150000},
                {"category": "Clothing", "items": 120, "value": 60000},
                {"category": "Books", "items": 100, "value": 20000},
                {"category": "Home & Garden", "items": 80, "value": 15000},
                {"category": "Sports", "items": 50, "value": 10000},
            ]

            return {
                "summary": {
                    "total_records": total_products,
                    "date_range": {
                        "start_date": date_range.get("start_date").strftime("%Y-%m-%d"),
                        "end_date": date_range.get("end_date").strftime("%Y-%m-%d"),
                    },
                    "key_metrics": {
                        "total_products": total_products,
                        "low_stock_items": low_stock_items,
                        "out_of_stock_items": out_of_stock_items,
                        "inventory_value": f"${inventory_value:,.2f}",
                        "turnover_rate": "4.2x",
                        "stock_accuracy": "98.5%",
                    },
                    "trends": {
                        "stock_levels": "stable",
                        "turnover_trend": "increasing",
                        "low_stock_trend": "decreasing",
                    },
                },
                "charts": {
                    "stock_movements": {
                        "chart_type": "line",
                        "title": "Stock Movements",
                        "data": stock_movements,
                        "x_axis_label": "Date",
                        "y_axis_label": "Quantity",
                    },
                    "category_breakdown": {
                        "chart_type": "donut",
                        "title": "Inventory by Category",
                        "data": category_breakdown,
                        "x_axis_label": "Category",
                        "y_axis_label": "Value",
                    },
                },
                "raw_data": stock_movements + category_breakdown,
            }

        except Exception as e:
            logger.error(f"Error generating inventory status: {e}")
            return self._get_empty_report_data()

    async def _generate_user_activity(
        self,
        filters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Generate user activity report."""
        try:
            date_range = self._get_date_range(filters)

            # Get actual user data from database
            user_stats = await self.db.execute(
                select(
                    func.count(User.id).label("total_users"),
                    func.count(User.id).filter(User.is_active).label("active_users"),
                ),
            )
            user_counts = user_stats.fetchone()

            # Get login activity from audit logs
            login_activity = await self.db.execute(
                select(
                    func.count(AuditLog.id).label("login_count"),
                    func.strftime("%Y-%m-%d", AuditLog.timestamp).label("date"),
                )
                .where(
                    and_(
                        AuditLog.action.in_(["login_success", "login_attempt"]),
                        AuditLog.timestamp >= date_range.get("start_date"),
                        AuditLog.timestamp <= date_range.get("end_date"),
                    ),
                )
                .group_by(func.strftime("%Y-%m-%d", AuditLog.timestamp))
                .order_by(func.strftime("%Y-%m-%d", AuditLog.timestamp)),
            )

            login_data = []
            for row in login_activity:
                login_data.append({"date": row.date, "logins": row.login_count})

            # Mock feature usage data
            feature_usage = {
                "dashboard_views": 1250,
                "report_generation": 340,
                "user_management": 89,
                "inventory_updates": 567,
                "order_processing": 234,
            }

            # Mock user growth data
            user_growth = []
            for i in range(30):
                current_date = date_range.get("start_date") + timedelta(days=i)
                user_growth.append(
                    {
                        "date": current_date.strftime("%Y-%m-%d"),
                        "new_users": 2 + i % 5,
                        "total_users": 50 + i * 2,
                    },
                )

            return {
                "summary": {
                    "total_records": user_counts.total_users,
                    "date_range": {
                        "start_date": date_range.get("start_date").strftime("%Y-%m-%d"),
                        "end_date": date_range.get("end_date").strftime("%Y-%m-%d"),
                    },
                    "key_metrics": {
                        "total_users": user_counts.total_users,
                        "active_users": user_counts.active_users,
                        "user_growth_rate": "15.2%",
                        "avg_session_duration": "24m 15s",
                        "feature_adoption_rate": "87.3%",
                    },
                    "trends": {
                        "user_activity": "increasing",
                        "feature_usage": "expanding",
                        "retention_rate": "improving",
                    },
                },
                "charts": {
                    "user_growth": {
                        "chart_type": "line",
                        "title": "User Growth",
                        "data": user_growth,
                        "x_axis_label": "Date",
                        "y_axis_label": "Users",
                    },
                    "feature_usage": {
                        "chart_type": "bar",
                        "title": "Feature Usage",
                        "data": [
                            {"feature": k, "usage": v} for k, v in feature_usage.items()
                        ],
                        "x_axis_label": "Feature",
                        "y_axis_label": "Usage Count",
                    },
                },
                "raw_data": login_data
                + [{"feature": k, "usage": v} for k, v in feature_usage.items()],
            }

        except Exception as e:
            logger.error(f"Error generating user activity: {e}")
            return self._get_empty_report_data()

    async def _generate_financial_summary(
        self,
        filters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Generate financial summary report."""
        try:
            date_range = self._get_date_range(filters)

            # Mock financial data
            total_revenue = 125000.00
            total_costs = 85000.00
            gross_profit = 40000.00
            profit_margin = 32.0

            # Mock monthly revenue
            revenue_by_month = []
            for i in range(12):
                month_date = datetime.now(UTC).replace(month=i + 1, day=1)
                revenue_by_month.append(
                    {
                        "month": month_date.strftime("%Y-%m"),
                        "revenue": 8000 + i * 500,
                        "costs": 6000 + i * 300,
                        "profit": 2000 + i * 200,
                    },
                )

            # Mock expense categories
            expense_categories = [
                {"category": "Inventory", "amount": 35000, "percentage": 41.2},
                {"category": "Operations", "amount": 25000, "percentage": 29.4},
                {"category": "Marketing", "amount": 15000, "percentage": 17.6},
                {"category": "Personnel", "amount": 10000, "percentage": 11.8},
            ]

            # Mock cash flow
            cash_flow = []
            current_cash = 50000
            for i in range(30):
                current_date = date_range.get("start_date") + timedelta(days=i)
                inflow = 1000 + i * 50
                outflow = 800 + i * 30
                current_cash = current_cash + inflow - outflow
                cash_flow.append(
                    {
                        "date": current_date.strftime("%Y-%m-%d"),
                        "inflow": inflow,
                        "outflow": outflow,
                        "net_flow": inflow - outflow,
                        "balance": current_cash,
                    },
                )

            return {
                "summary": {
                    "total_records": len(revenue_by_month),
                    "date_range": {
                        "start_date": date_range.get("start_date").strftime("%Y-%m-%d"),
                        "end_date": date_range.get("end_date").strftime("%Y-%m-%d"),
                    },
                    "key_metrics": {
                        "total_revenue": f"${total_revenue:,.2f}",
                        "total_costs": f"${total_costs:,.2f}",
                        "gross_profit": f"${gross_profit:,.2f}",
                        "profit_margin": f"{profit_margin:.1f}%",
                        "roi": "32.5%",
                        "break_even": "8 months",
                    },
                    "trends": {
                        "revenue_trend": "increasing",
                        "cost_trend": "decreasing",
                        "profit_trend": "improving",
                    },
                },
                "charts": {
                    "revenue_trend": {
                        "chart_type": "area",
                        "title": "Revenue Trend",
                        "data": revenue_by_month,
                        "x_axis_label": "Month",
                        "y_axis_label": "Amount",
                    },
                    "expense_breakdown": {
                        "chart_type": "pie",
                        "title": "Expense Categories",
                        "data": expense_categories,
                        "x_axis_label": "Category",
                        "y_axis_label": "Amount",
                    },
                    "cash_flow": {
                        "chart_type": "line",
                        "title": "Cash Flow",
                        "data": cash_flow,
                        "x_axis_label": "Date",
                        "y_axis_label": "Balance",
                    },
                },
                "raw_data": revenue_by_month + expense_categories + cash_flow,
            }

        except Exception as e:
            logger.error(f"Error generating financial summary: {e}")
            return self._get_empty_report_data()

    async def _generate_system_metrics(
        self,
        filters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Generate system metrics report."""
        try:
            date_range = self._get_date_range(filters)

            # Mock system metrics data
            system_metrics = []
            for i in range(24):
                current_time = datetime.now(UTC) - timedelta(hours=23 - i)
                system_metrics.append(
                    {
                        "timestamp": current_time.strftime("%Y-%m-%d %H:%M"),
                        "cpu_usage": 45 + (i % 20),  # Mock variation
                        "memory_usage": 60 + (i % 15),
                        "disk_usage": 25 + (i % 10),
                        "response_time": 100 + (i % 50),
                        "error_rate": 0.5 + (i % 2) * 0.1,
                    },
                )

            # Mock error breakdown
            error_breakdown = [
                {"error_type": "Database Connection", "count": 25, "percentage": 35.2},
                {"error_type": "API Timeout", "count": 20, "percentage": 28.2},
                {"error_type": "Validation Error", "count": 15, "percentage": 21.1},
                {"error_type": "Authentication Error", "count": 11, "percentage": 15.5},
            ]

            # Mock performance metrics
            performance_metrics = {
                "avg_response_time": "127ms",
                "p95_response_time": "289ms",
                "p99_response_time": "450ms",
                "requests_per_second": 1250,
                "error_rate": "0.7%",
                "uptime": "99.9%",
            }

            return {
                "summary": {
                    "total_records": len(system_metrics),
                    "date_range": {
                        "start_date": date_range.get("start_date").strftime("%Y-%m-%d"),
                        "end_date": date_range.get("end_date").strftime("%Y-%m-%d"),
                    },
                    "key_metrics": performance_metrics,
                    "trends": {
                        "response_time": "stable",
                        "error_rate": "decreasing",
                        "system_load": "increasing",
                    },
                },
                "charts": {
                    "system_metrics": {
                        "chart_type": "line",
                        "title": "System Performance",
                        "data": system_metrics,
                        "x_axis_label": "Time",
                        "y_axis_label": "Usage %",
                    },
                    "error_breakdown": {
                        "chart_type": "pie",
                        "title": "Error Types",
                        "data": error_breakdown,
                        "x_axis_label": "Error Type",
                        "y_axis_label": "Count",
                    },
                },
                "raw_data": system_metrics + error_breakdown,
            }

        except Exception as e:
            logger.error(f"Error generating system metrics: {e}")
            return self._get_empty_report_data()

    def _get_date_range(
        self,
        filters: dict[str, Any] | None = None,
    ) -> dict[str, date]:
        """Get date range from filters or use defaults."""
        if filters and "date_range" in filters:
            start_date = filters["date_range"].get(
                "start_date",
                date.today() - timedelta(days=30),
            )
            end_date = filters["date_range"].get("end_date", date.today())
        else:
            start_date = date.today() - timedelta(days=30)
            end_date = date.today()

        return {"start_date": start_date, "end_date": end_date}

    def _get_empty_report_data(self) -> dict[str, Any]:
        """Get empty report data structure for error cases."""
        return {
            "summary": {
                "total_records": 0,
                "date_range": {
                    "start_date": date.today().strftime("%Y-%m-%d"),
                    "end_date": date.today().strftime("%Y-%m-%d"),
                },
                "key_metrics": {},
                "trends": {},
            },
            "charts": {},
            "raw_data": [],
        }

    async def get_available_reports(self) -> list[dict[str, Any]]:
        """Get list of available report types."""
        return [
            {
                "type": "sales_overview",
                "name": "Sales Overview",
                "description": "Comprehensive sales performance and trends",
                "category": "Sales",
                "charts": ["line", "bar", "pie"],
            },
            {
                "type": "inventory_status",
                "name": "Inventory Status",
                "description": "Current inventory levels and stock movements",
                "category": "Inventory",
                "charts": ["line", "donut"],
            },
            {
                "type": "user_activity",
                "name": "User Activity",
                "description": "User engagement and system usage analytics",
                "category": "Users",
                "charts": ["line", "bar"],
            },
            {
                "type": "financial_summary",
                "name": "Financial Summary",
                "description": "Revenue, costs, and profit analysis",
                "category": "Finance",
                "charts": ["area", "pie", "line"],
            },
            {
                "type": "system_metrics",
                "name": "System Metrics",
                "description": "Performance monitoring and system health",
                "category": "System",
                "charts": ["line", "pie"],
            },
        ]

    async def export_report(
        self,
        report_data: dict[str, Any],
        export_format: str,
        filename: str | None = None,
    ) -> bytes:
        """Export report data to specified format."""
        try:
            if export_format == "json":
                return json.dumps(report_data, indent=2, default=str).encode("utf-8")
            if export_format == "csv":
                return self._export_to_csv(report_data)
            if export_format == "excel":
                return self._export_to_excel(report_data)
            if export_format == "pdf":
                return await self._export_to_pdf(report_data)
            raise ValueError(f"Unsupported export format: {export_format}")

        except Exception as e:
            logger.error(f"Error exporting report: {e}")
            raise

    def _export_to_csv(self, report_data: dict[str, Any]) -> bytes:
        """Export report data to CSV format."""
        import csv
        import io

        output = io.StringIO()

        # Write summary data
        if "summary" in report_data:
            writer = csv.writer(output)
            writer.writerow(["Summary"])
            writer.writerow(["Key Metrics"])
            for key, value in report_data["summary"]["key_metrics"].items():
                writer.writerow([key, value])

        # Write raw data if available
        if report_data.get("raw_data"):
            writer.writerow([])
            writer.writerow(["Raw Data"])
            if isinstance(report_data["raw_data"][0], dict):
                fieldnames = report_data["raw_data"][0].keys()
                writer = csv.DictWriter(output, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(report_data["raw_data"])

        return output.getvalue().encode("utf-8")

    def _export_to_excel(self, report_data: dict[str, Any]) -> bytes:
        """Export report data to Excel format."""
        try:
            import io

            import pandas as pd

            # Create Excel writer
            output = io.BytesIO()

            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                # Summary sheet
                if "summary" in report_data:
                    summary_data = []
                    for key, value in report_data["summary"]["key_metrics"].items():
                        summary_data.append({"Metric": key, "Value": value})

                    df_summary = pd.DataFrame(summary_data)
                    df_summary.to_excel(writer, sheet_name="Summary", index=False)

                # Raw data sheet
                if report_data.get("raw_data"):
                    df_raw = pd.DataFrame(report_data["raw_data"])
                    df_raw.to_excel(writer, sheet_name="Raw Data", index=False)

            return output.getvalue()

        except ImportError as e:
            raise ValueError("Excel export requires pandas and openpyxl") from e

    async def _export_to_pdf(self, report_data: dict[str, Any]) -> bytes:
        """Export report data to PDF format."""
        try:
            import io

            from reportlab.lib import colors
            from reportlab.lib.pagesizes import letter
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.platypus import (
                Paragraph,
                SimpleDocTemplate,
                Spacer,
                Table,
                TableStyle,
            )

            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter)
            styles = getSampleStyleSheet()

            story = []

            # Title
            title = report_data.get("title", "Report")
            story.append(Paragraph(title, styles["Heading1"]))
            story.append(Spacer(1, 12))

            # Summary
            if "summary" in report_data:
                story.append(Paragraph("Summary", styles["Heading2"]))
                story.append(Spacer(1, 6))

                # Key metrics table
                metrics_data = [["Metric", "Value"]]
                for key, value in report_data["summary"]["key_metrics"].items():
                    metrics_data.append([key, str(value)])

                metrics_table = Table(metrics_data)
                metrics_table.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                            ("FONTSIZE", (0, 0), (-1, 0), 14),
                            ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                            ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                            ("GRID", (0, 0), (-1, -1), 1, colors.black),
                        ],
                    ),
                )
                story.append(metrics_table)
                story.append(Spacer(1, 12))

            doc.build(story)
            return buffer.getvalue()

        except ImportError as e:
            raise ValueError("PDF export requires reportlab") from e

    async def schedule_report(
        self,
        report_config: dict[str, Any],
        schedule_config: dict[str, Any],
        recipients: list[str],
    ) -> str:
        """Schedule a report for automated generation."""
        try:
            schedule_id = str(uuid.uuid4())

            # In a real implementation, this would save to database
            # For now, return schedule ID
            logger.info(f"Report scheduled: {schedule_id} for recipients: {recipients}")

            return schedule_id

        except Exception as e:
            logger.error(f"Error scheduling report: {e}")
            raise

    async def _get_customer_segments(
        self,
        start_date: date,
        end_date: date,
    ) -> list[dict[str, Any]]:
        """Get customer segments based on user roles and activity."""
        try:
            # Get user role distribution for customer segmentation
            role_segments = await self.db.execute(
                select(
                    Role.name.label("role_name"),
                    func.count(User.id).label("user_count"),
                )
                .join(User.roles)
                .where(User.is_active)
                .group_by(Role.name),
            )

            customer_segments = []
            total_users = 0

            for row in role_segments:
                # Mock revenue calculation based on role type
                revenue_multiplier = {
                    "admin": 10000,
                    "manager": 5000,
                    "user": 1000,
                    "guest": 500,
                }.get(row.role_name, 1000)

                segment_revenue = row.user_count * revenue_multiplier
                customer_segments.append(
                    {
                        "segment": row.role_name.title(),
                        "customers": row.user_count,
                        "revenue": segment_revenue,
                    },
                )
                total_users += row.user_count

            # Add individual segment if not already present
            if not any(s["segment"] == "Individual" for s in customer_segments):
                customer_segments.append(
                    {
                        "segment": "Individual",
                        "customers": max(
                            0,
                            total_users
                            - sum(s["customers"] for s in customer_segments),
                        ),
                        "revenue": 10000,
                    },
                )

            return customer_segments

        except Exception as e:
            logger.error(f"Error getting customer segments: {e}")
            # Return mock data as fallback
            return [
                {"segment": "Enterprise", "customers": 50, "revenue": 75000},
                {"segment": "SMB", "customers": 200, "revenue": 40000},
                {"segment": "Individual", "customers": 300, "revenue": 10000},
            ]

    async def _get_inventory_metrics(
        self,
        start_date: date,
        end_date: date,
    ) -> dict[str, Any]:
        """Get inventory metrics from database."""
        try:
            # Get product count
            product_count = await self.db.execute(select(func.count(Product.id)))
            total_products = product_count.scalar() or 0

            # Get products with low stock (mock - would need stock levels)
            low_stock_items = min(25, total_products // 20)  # Mock calculation

            # Get category breakdown
            category_breakdown = await self.db.execute(
                select(
                    Category.name.label("category"),
                    func.count(Product.id).label("item_count"),
                )
                .join(Product.categories)
                .group_by(Category.name)
                .limit(5),
            )

            categories = []
            for row in category_breakdown:
                categories.append(
                    {
                        "category": row.category or "Uncategorized",
                        "items": row.item_count,
                        "value": row.item_count * 1000,  # Mock value calculation
                    },
                )

            return {
                "total_products": total_products,
                "low_stock_items": low_stock_items,
                "category_breakdown": categories,
            }

        except Exception as e:
            logger.error(f"Error getting inventory metrics: {e}")
            return {"total_products": 0, "low_stock_items": 0, "category_breakdown": []}
