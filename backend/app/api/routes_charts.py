from fastapi import APIRouter, HTTPException
from app.data.charts import CHARTS

router = APIRouter(
    prefix="/api/charts",
    tags=["Charts"],
)


@router.get("/")
def get_charts():
    return CHARTS


@router.get("/{chart_id}")
def get_chart(chart_id: int):
    chart = next(
        (item for item in CHARTS if item["id"] == chart_id),
        None,
    )

    if chart is None:
        raise HTTPException(
            status_code=404,
            detail="چارت پیدا نشد",
        )

    return chart