from decimal import Decimal
from typing import Iterable
from app.models.time_series import TimeSeriesPoint

class AggregationResult:
    def __init__(self):
        self.count: int = 0
        self.min_close: Decimal | None = None
        self.max_close: Decimal | None = None
        self.avg_close: Decimal | None = None
        self.total_volume: int = 0

def compute_aggregations(points: Iterable[TimeSeriesPoint]) -> AggregationResult:
    result = AggregationResult()
    close_values: list[Decimal] = []
    total_volume = 0

    for point in points:
        result.count += 1
        if point.close_price is not None:
            close_values.append(point.close_price)
        if point.volume is not None:
            total_volume += point.volume
    
    if close_values:
        result.min_close = min(close_values)
        result.max_close = max(close_values)
        result.avg_close = sum(close_values) / len(close_values)
    
    result.total_volume = total_volume
    return result