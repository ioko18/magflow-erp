"""Advanced reporting schemas for MagFlow ERP."""

from datetime import date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ChartType(str, Enum):
    """Chart types for reports."""

    BAR = "bar"
    LINE = "line"
    PIE = "pie"
    DONUT = "donut"
    AREA = "area"
    SCATTER = "scatter"
    TABLE = "table"


class ReportType(str, Enum):
    """Report types available in the system."""

    SALES_OVERVIEW = "sales_overview"
    INVENTORY_STATUS = "inventory_status"
    USER_ACTIVITY = "user_activity"
    FINANCIAL_SUMMARY = "financial_summary"
    PRODUCT_PERFORMANCE = "product_performance"
    CUSTOMER_ANALYTICS = "customer_analytics"
    PURCHASE_TRENDS = "purchase_trends"
    SYSTEM_METRICS = "system_metrics"


class DateRange(BaseModel):
    """Date range for report filtering."""

    start_date: date = Field(..., description="Start date for the report")
    end_date: date = Field(..., description="End date for the report")

    model_config = ConfigDict(from_attributes=True)


class ChartData(BaseModel):
    """Chart data for visualization."""

    chart_type: ChartType = Field(..., description="Type of chart")
    title: str = Field(..., description="Chart title")
    data: dict[str, Any] = Field(..., description="Chart data")
    x_axis_label: str | None = Field(None, description="X-axis label")
    y_axis_label: str | None = Field(None, description="Y-axis label")
    colors: list[str] | None = Field(None, description="Chart colors")

    model_config = ConfigDict(from_attributes=True)


class ReportFilter(BaseModel):
    """Filters for report generation."""

    date_range: DateRange | None = Field(None, description="Date range filter")
    user_ids: list[int] | None = Field(None, description="Filter by user IDs")
    product_ids: list[int] | None = Field(None, description="Filter by product IDs")
    category_ids: list[int] | None = Field(
        None,
        description="Filter by category IDs",
    )
    status: list[str] | None = Field(None, description="Filter by status")
    custom_filters: dict[str, Any] | None = Field(None, description="Custom filters")

    model_config = ConfigDict(from_attributes=True)


class ReportConfig(BaseModel):
    """Report configuration."""

    report_type: ReportType = Field(..., description="Type of report")
    filters: ReportFilter | None = Field(None, description="Report filters")
    charts: list[ChartType] = Field(..., description="Chart types to include")
    include_raw_data: bool = Field(False, description="Include raw data in response")
    group_by: list[str] | None = Field(None, description="Group data by fields")
    sort_by: str | None = Field(None, description="Sort data by field")
    sort_order: str = Field("desc", description="Sort order (asc/desc)")

    model_config = ConfigDict(from_attributes=True)


class ReportDataPoint(BaseModel):
    """Single data point in a report."""

    label: str = Field(..., description="Data point label")
    value: int | float | str = Field(..., description="Data point value")
    category: str | None = Field(None, description="Data point category")
    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")

    model_config = ConfigDict(from_attributes=True)


class ReportSeries(BaseModel):
    """Series of data points for charts."""

    name: str = Field(..., description="Series name")
    data: list[ReportDataPoint] = Field(..., description="Data points")
    color: str | None = Field(None, description="Series color")

    model_config = ConfigDict(from_attributes=True)


class ReportSummary(BaseModel):
    """Summary statistics for a report."""

    total_records: int = Field(..., description="Total number of records")
    date_range: DateRange = Field(..., description="Date range of data")
    key_metrics: dict[str, int | float | str] = Field(
        ...,
        description="Key metrics",
    )
    trends: dict[str, Any] | None = Field(None, description="Trend analysis")

    model_config = ConfigDict(from_attributes=True)


class Report(BaseModel):
    """Complete report structure."""

    id: str = Field(..., description="Report ID")
    title: str = Field(..., description="Report title")
    description: str | None = Field(None, description="Report description")
    report_type: ReportType = Field(..., description="Type of report")
    config: ReportConfig = Field(..., description="Report configuration")
    summary: ReportSummary = Field(..., description="Report summary")
    charts: list[ChartData] = Field(..., description="Chart data")
    raw_data: list[dict[str, Any]] | None = Field(None, description="Raw data")
    generated_at: datetime = Field(..., description="Report generation time")
    generated_by: int = Field(..., description="User ID who generated the report")

    model_config = ConfigDict(from_attributes=True)


class SalesReportData(BaseModel):
    """Sales-specific report data."""

    total_orders: int = Field(..., description="Total number of orders")
    total_revenue: float = Field(..., description="Total revenue")
    average_order_value: float = Field(..., description="Average order value")
    top_products: list[dict[str, Any]] = Field(
        ...,
        description="Top performing products",
    )
    sales_by_period: list[dict[str, Any]] = Field(
        ...,
        description="Sales data by time period",
    )
    customer_segments: list[dict[str, Any]] = Field(
        ...,
        description="Customer segment analysis",
    )

    model_config = ConfigDict(from_attributes=True)


class InventoryReportData(BaseModel):
    """Inventory-specific report data."""

    total_products: int = Field(..., description="Total number of products")
    low_stock_items: int = Field(..., description="Items with low stock")
    out_of_stock_items: int = Field(..., description="Items out of stock")
    inventory_value: float = Field(..., description="Total inventory value")
    stock_movements: list[dict[str, Any]] = Field(
        ...,
        description="Stock movement history",
    )
    category_breakdown: list[dict[str, Any]] = Field(
        ...,
        description="Inventory by category",
    )

    model_config = ConfigDict(from_attributes=True)


class UserActivityReportData(BaseModel):
    """User activity report data."""

    total_users: int = Field(..., description="Total number of users")
    active_users: int = Field(..., description="Active users")
    user_growth: float = Field(..., description="User growth percentage")
    login_frequency: dict[str, int] = Field(..., description="Login frequency data")
    feature_usage: dict[str, int] = Field(..., description="Feature usage statistics")
    geographic_distribution: dict[str, int] | None = Field(
        None,
        description="User geographic data",
    )

    model_config = ConfigDict(from_attributes=True)


class FinancialReportData(BaseModel):
    """Financial report data."""

    total_revenue: float = Field(..., description="Total revenue")
    total_costs: float = Field(..., description="Total costs")
    gross_profit: float = Field(..., description="Gross profit")
    profit_margin: float = Field(..., description="Profit margin percentage")
    revenue_by_month: list[dict[str, Any]] = Field(..., description="Monthly revenue")
    expense_categories: list[dict[str, Any]] = Field(
        ...,
        description="Expense breakdown",
    )
    cash_flow: list[dict[str, Any]] = Field(..., description="Cash flow data")

    model_config = ConfigDict(from_attributes=True)


class ExportFormat(str, Enum):
    """Export format options."""

    PDF = "pdf"
    EXCEL = "excel"
    CSV = "csv"
    JSON = "json"


class ExportRequest(BaseModel):
    """Request for exporting report data."""

    report_id: str = Field(..., description="Report ID to export")
    format: ExportFormat = Field(..., description="Export format")
    include_charts: bool = Field(True, description="Include charts in export")
    filename: str | None = Field(None, description="Custom filename")

    model_config = ConfigDict(from_attributes=True)


class ExportResponse(BaseModel):
    """Response for export request."""

    export_id: str = Field(..., description="Export job ID")
    status: str = Field(..., description="Export status")
    download_url: str | None = Field(None, description="Download URL")
    message: str = Field(..., description="Status message")

    model_config = ConfigDict(from_attributes=True)


class ScheduledReport(BaseModel):
    """Scheduled report configuration."""

    id: str = Field(..., description="Schedule ID")
    name: str = Field(..., description="Schedule name")
    report_type: ReportType = Field(..., description="Report type")
    config: ReportConfig = Field(..., description="Report configuration")
    schedule_type: str = Field(
        ...,
        description="Schedule type (daily, weekly, monthly)",
    )
    schedule_time: str = Field(..., description="Schedule time (HH:MM)")
    recipients: list[str] = Field(..., description="Email recipients")
    is_active: bool = Field(..., description="Whether schedule is active")
    last_run: datetime | None = Field(None, description="Last run time")
    next_run: datetime | None = Field(None, description="Next scheduled run")

    model_config = ConfigDict(from_attributes=True)


class ReportTemplate(BaseModel):
    """Report template for customization."""

    id: str = Field(..., description="Template ID")
    name: str = Field(..., description="Template name")
    description: str | None = Field(None, description="Template description")
    report_type: ReportType = Field(..., description="Report type")
    config: ReportConfig = Field(..., description="Default configuration")
    charts_config: dict[str, Any] = Field(..., description="Chart configurations")
    is_default: bool = Field(False, description="Whether this is the default template")
    created_by: int = Field(..., description="User who created the template")
    created_at: datetime = Field(..., description="Creation time")

    model_config = ConfigDict(from_attributes=True)
