"""Advanced reporting API endpoints for MagFlow ERP."""

import uuid
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..api.auth import get_current_active_user
from ..core.database import get_async_session
from ..db.models import User as UserModel
from ..schemas.reporting import (
    ChartType,
    ExportRequest,
    ExportResponse,
    Report,
    ReportConfig,
    ReportType,
)
from ..services.reporting_service import ReportingService

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/available")
async def get_available_reports(
    current_user: UserModel = Depends(get_current_active_user),
) -> list[dict[str, Any]]:
    """Get list of available report types.

    - **Returns**: List of available report types with descriptions
    """
    reporting_service = ReportingService(
        None,
    )  # We'll pass None for now since we don't need DB for this
    return await reporting_service.get_available_reports()


@router.post("/generate", response_model=Report)
async def generate_report(
    report_config: ReportConfig,
    background_tasks: BackgroundTasks,
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_session),
) -> Report:
    """Generate a report based on configuration.

    - **report_config**: Configuration for the report to generate
    - **Returns**: Generated report with data and charts
    """
    try:
        reporting_service = ReportingService(db)

        # Generate the report
        report_data = await reporting_service.generate_report(
            report_type=report_config.report_type.value,
            filters=report_config.filters.dict() if report_config.filters else None,
            user_id=current_user.id,
        )

        # Convert to Report model
        return Report(
            id=report_data["report_id"],
            title=f"{report_config.report_type.value.replace('_', ' ').title()} Report",
            description=f"Report generated for {report_config.report_type.value}",
            report_type=report_config.report_type,
            config=report_config,
            summary=report_data["summary"],
            charts=report_data["charts"],
            raw_data=report_data.get("raw_data"),
            generated_at=datetime.fromisoformat(report_data["generated_at"]),
            generated_by=current_user.id,
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate report: {e!s}",
        )


@router.get("/sales/overview", response_model=Report)
async def get_sales_overview(
    start_date: str | None = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: str | None = Query(None, description="End date (YYYY-MM-DD)"),
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_session),
) -> Report:
    """Get sales overview report.

    - **start_date**: Start date for the report period
    - **end_date**: End date for the report period
    """
    try:
        reporting_service = ReportingService(db)

        # Build filters
        filters = {}
        if start_date or end_date:
            from datetime import date

            filters["date_range"] = {
                "start_date": (
                    date.fromisoformat(start_date)
                    if start_date
                    else date.today() - timedelta(days=30)
                ),
                "end_date": date.fromisoformat(end_date) if end_date else date.today(),
            }

        # Generate report
        report_data = await reporting_service.generate_report(
            report_type="sales_overview",
            filters=filters,
            user_id=current_user.id,
        )

        # Convert to Report model
        return Report(
            id=report_data["report_id"],
            title="Sales Overview Report",
            description="Comprehensive sales performance and trends",
            report_type=ReportType.SALES_OVERVIEW,
            config=ReportConfig(
                report_type=ReportType.SALES_OVERVIEW,
                charts=[ChartType.LINE, ChartType.BAR, ChartType.PIE],
            ),
            summary=report_data["summary"],
            charts=report_data["charts"],
            raw_data=report_data.get("raw_data"),
            generated_at=datetime.fromisoformat(report_data["generated_at"]),
            generated_by=current_user.id,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate sales report: {e!s}",
        )


@router.get("/inventory/status", response_model=Report)
async def get_inventory_status(
    start_date: str | None = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: str | None = Query(None, description="End date (YYYY-MM-DD)"),
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_session),
) -> Report:
    """Get inventory status report.

    - **start_date**: Start date for the report period
    - **end_date**: End date for the report period
    """
    try:
        reporting_service = ReportingService(db)

        # Build filters
        filters = {}
        if start_date or end_date:
            from datetime import date

            filters["date_range"] = {
                "start_date": (
                    date.fromisoformat(start_date)
                    if start_date
                    else date.today() - timedelta(days=30)
                ),
                "end_date": date.fromisoformat(end_date) if end_date else date.today(),
            }

        # Generate report
        report_data = await reporting_service.generate_report(
            report_type="inventory_status",
            filters=filters,
            user_id=current_user.id,
        )

        # Convert to Report model
        return Report(
            id=report_data["report_id"],
            title="Inventory Status Report",
            description="Current inventory levels and stock movements",
            report_type=ReportType.INVENTORY_STATUS,
            config=ReportConfig(
                report_type=ReportType.INVENTORY_STATUS,
                charts=[ChartType.LINE, ChartType.DONUT],
            ),
            summary=report_data["summary"],
            charts=report_data["charts"],
            raw_data=report_data.get("raw_data"),
            generated_at=datetime.fromisoformat(report_data["generated_at"]),
            generated_by=current_user.id,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate inventory report: {e!s}",
        )


@router.get("/users/activity", response_model=Report)
async def get_user_activity(
    start_date: str | None = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: str | None = Query(None, description="End date (YYYY-MM-DD)"),
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_session),
) -> Report:
    """Get user activity report.

    - **start_date**: Start date for the report period
    - **end_date**: End date for the report period
    """
    try:
        reporting_service = ReportingService(db)

        # Build filters
        filters = {}
        if start_date or end_date:
            from datetime import date

            filters["date_range"] = {
                "start_date": (
                    date.fromisoformat(start_date)
                    if start_date
                    else date.today() - timedelta(days=30)
                ),
                "end_date": date.fromisoformat(end_date) if end_date else date.today(),
            }

        # Generate report
        report_data = await reporting_service.generate_report(
            report_type="user_activity",
            filters=filters,
            user_id=current_user.id,
        )

        # Convert to Report model
        return Report(
            id=report_data["report_id"],
            title="User Activity Report",
            description="User engagement and system usage analytics",
            report_type=ReportType.USER_ACTIVITY,
            config=ReportConfig(
                report_type=ReportType.USER_ACTIVITY,
                charts=[ChartType.LINE, ChartType.BAR],
            ),
            summary=report_data["summary"],
            charts=report_data["charts"],
            raw_data=report_data.get("raw_data"),
            generated_at=datetime.fromisoformat(report_data["generated_at"]),
            generated_by=current_user.id,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate user activity report: {e!s}",
        )


@router.get("/financial/summary", response_model=Report)
async def get_financial_summary(
    start_date: str | None = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: str | None = Query(None, description="End date (YYYY-MM-DD)"),
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_session),
) -> Report:
    """Get financial summary report.

    - **start_date**: Start date for the report period
    - **end_date**: End date for the report period
    """
    try:
        reporting_service = ReportingService(db)

        # Build filters
        filters = {}
        if start_date or end_date:
            from datetime import date

            filters["date_range"] = {
                "start_date": (
                    date.fromisoformat(start_date)
                    if start_date
                    else date.today() - timedelta(days=30)
                ),
                "end_date": date.fromisoformat(end_date) if end_date else date.today(),
            }

        # Generate report
        report_data = await reporting_service.generate_report(
            report_type="financial_summary",
            filters=filters,
            user_id=current_user.id,
        )

        # Convert to Report model
        return Report(
            id=report_data["report_id"],
            title="Financial Summary Report",
            description="Revenue, costs, and profit analysis",
            report_type=ReportType.FINANCIAL_SUMMARY,
            config=ReportConfig(
                report_type=ReportType.FINANCIAL_SUMMARY,
                charts=[ChartType.AREA, ChartType.PIE, ChartType.LINE],
            ),
            summary=report_data["summary"],
            charts=report_data["charts"],
            raw_data=report_data.get("raw_data"),
            generated_at=datetime.fromisoformat(report_data["generated_at"]),
            generated_by=current_user.id,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate financial report: {e!s}",
        )


@router.get("/system/metrics", response_model=Report)
async def get_system_metrics(
    start_date: str | None = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: str | None = Query(None, description="End date (YYYY-MM-DD)"),
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_session),
) -> Report:
    """Get system metrics report.

    - **start_date**: Start date for the report period
    - **end_date**: End date for the report period
    """
    try:
        reporting_service = ReportingService(db)

        # Build filters
        filters = {}
        if start_date or end_date:
            from datetime import date

            filters["date_range"] = {
                "start_date": (
                    date.fromisoformat(start_date)
                    if start_date
                    else date.today() - timedelta(days=30)
                ),
                "end_date": date.fromisoformat(end_date) if end_date else date.today(),
            }

        # Generate report
        report_data = await reporting_service.generate_report(
            report_type="system_metrics",
            filters=filters,
            user_id=current_user.id,
        )

        # Convert to Report model
        return Report(
            id=report_data["report_id"],
            title="System Metrics Report",
            description="Performance monitoring and system health",
            report_type=ReportType.SYSTEM_METRICS,
            config=ReportConfig(
                report_type=ReportType.SYSTEM_METRICS,
                charts=[ChartType.LINE, ChartType.PIE],
            ),
            summary=report_data["summary"],
            charts=report_data["charts"],
            raw_data=report_data.get("raw_data"),
            generated_at=datetime.fromisoformat(report_data["generated_at"]),
            generated_by=current_user.id,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate system metrics report: {e!s}",
        )


@router.post("/export", response_model=ExportResponse)
async def export_report(
    export_request: ExportRequest,
    background_tasks: BackgroundTasks,
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_session),
) -> ExportResponse:
    """Export a report to specified format.

    - **export_request**: Export configuration including report ID and format
    """
    try:
        reporting_service = ReportingService(db)

        # Generate the report first
        report_data = await reporting_service.generate_report(
            report_type="sales_overview",  # This should be extracted from report ID
            user_id=current_user.id,
        )

        # Export the report
        _ = await reporting_service.export_report(
            report_data,
            export_request.format.value,
            export_request.filename,
        )

        # In a real implementation, this would save to file storage and return URL
        # For now, return mock response
        export_id = str(uuid.uuid4())

        return ExportResponse(
            export_id=export_id,
            status="completed",
            download_url=f"/api/v1/reports/download/{export_id}",
            message=f"Report exported successfully in {export_request.format.value} format",
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export report: {e!s}",
        )


@router.post("/schedule")
async def schedule_report(
    report_config: ReportConfig,
    schedule_config: dict[str, Any],
    recipients: list[str],
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_session),
) -> dict[str, str]:
    """Schedule a report for automated generation and delivery.

    - **report_config**: Configuration for the report
    - **schedule_config**: Scheduling configuration (type, time, frequency)
    - **recipients**: List of email addresses to receive the report
    """
    try:
        reporting_service = ReportingService(db)

        schedule_id = await reporting_service.schedule_report(
            report_config.dict(),
            schedule_config,
            recipients,
        )

        return {"message": "Report scheduled successfully", "schedule_id": schedule_id}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to schedule report: {e!s}",
        )


@router.get("/templates")
async def get_report_templates(
    current_user: UserModel = Depends(get_current_active_user),
) -> list[dict[str, Any]]:
    """Get available report templates.

    - **Returns**: List of pre-configured report templates
    """
    # Mock templates data
    templates = [
        {
            "id": "sales_weekly",
            "name": "Weekly Sales Summary",
            "description": "Automated weekly sales performance report",
            "report_type": "sales_overview",
            "config": {
                "report_type": "sales_overview",
                "charts": ["line", "bar"],
                "include_raw_data": True,
            },
            "is_default": True,
        },
        {
            "id": "inventory_monthly",
            "name": "Monthly Inventory Report",
            "description": "Monthly inventory status and trends",
            "report_type": "inventory_status",
            "config": {
                "report_type": "inventory_status",
                "charts": ["donut", "line"],
                "include_raw_data": True,
            },
            "is_default": True,
        },
        {
            "id": "user_engagement",
            "name": "User Engagement Analysis",
            "description": "User activity and engagement metrics",
            "report_type": "user_activity",
            "config": {
                "report_type": "user_activity",
                "charts": ["line", "bar"],
                "include_raw_data": False,
            },
            "is_default": False,
        },
    ]

    return templates


@router.get("/dashboard/summary")
async def get_dashboard_summary(
    current_user: UserModel = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_session),
) -> dict[str, Any]:
    """Get dashboard summary for quick overview.

    - **Returns**: Key metrics and summary data for dashboard display
    """
    try:
        reporting_service = ReportingService(db)

        # Get summary data from different report types
        sales_data = await reporting_service._generate_sales_overview()
        inventory_data = await reporting_service._generate_inventory_status()
        user_data = await reporting_service._generate_user_activity()

        # Combine into dashboard summary
        return {
            "sales": {
                "total_revenue": sales_data["summary"]["key_metrics"].get(
                    "total_revenue",
                    "$0",
                ),
                "total_orders": sales_data["summary"]["key_metrics"].get(
                    "total_orders",
                    0,
                ),
                "average_order_value": sales_data["summary"]["key_metrics"].get(
                    "average_order_value",
                    "$0",
                ),
            },
            "inventory": {
                "total_products": inventory_data["summary"]["key_metrics"].get(
                    "total_products",
                    0,
                ),
                "low_stock_items": inventory_data["summary"]["key_metrics"].get(
                    "low_stock_items",
                    0,
                ),
                "inventory_value": inventory_data["summary"]["key_metrics"].get(
                    "inventory_value",
                    "$0",
                ),
            },
            "users": {
                "total_users": user_data["summary"]["key_metrics"].get(
                    "total_users",
                    0,
                ),
                "active_users": user_data["summary"]["key_metrics"].get(
                    "active_users",
                    0,
                ),
                "user_growth": user_data["summary"]["key_metrics"].get(
                    "user_growth_rate",
                    "0%",
                ),
            },
            "system": {
                "health_status": "healthy",
                "response_time": "127ms",
                "error_rate": "0.7%",
            },
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate dashboard summary: {e!s}",
        )
