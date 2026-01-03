"""Financial insights domain."""
from .router import router
from .service import InsightsService
from .models import (
    InsightType,
    InsightSeverity,
    Insight,
    SpendingTrend,
    CategoryInsight,
    AnomalyInsight,
    SavingsOpportunity,
    GeneratedInsight,
    InsightsReport,
)

__all__ = [
    'router',
    'InsightsService',
    'InsightType',
    'InsightSeverity',
    'Insight',
    'SpendingTrend',
    'CategoryInsight',
    'AnomalyInsight',
    'SavingsOpportunity',
    'GeneratedInsight',
    'InsightsReport',
]

