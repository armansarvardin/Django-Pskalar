from django.urls import path

from apps.finance.views import (
    DailyReportListView,
    ExpenseListCreateView,
    PaymentListCreateView,
    PaymentMethodListView,
    PaymentRefundView,
    ShiftCloseView,
    ShiftDetailView,
    ShiftListCreateView,
)

app_name = "finance"

urlpatterns = [
    path("payment-methods/", PaymentMethodListView.as_view(), name="payment-method-list"),
    path("shifts/", ShiftListCreateView.as_view(), name="shift-list"),
    path("shifts/<int:pk>/", ShiftDetailView.as_view(), name="shift-detail"),
    path("shifts/<int:pk>/close/", ShiftCloseView.as_view(), name="shift-close"),
    path("payments/", PaymentListCreateView.as_view(), name="payment-list"),
    path("payments/<int:pk>/refund/", PaymentRefundView.as_view(), name="payment-refund"),
    path("expenses/", ExpenseListCreateView.as_view(), name="expense-list"),
    path("reports/", DailyReportListView.as_view(), name="report-list"),
]