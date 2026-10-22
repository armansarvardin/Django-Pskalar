from django.db.models import QuerySet
from rest_framework import generics, status
from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from apps.finance.models import DailyReport, Expense, Payment, PaymentMethod, Shift
from apps.finance.serializers import (
    DailyReportFilterSerializer,
    DailyReportSerializer,
    ExpenseCreateSerializer,
    ExpenseSerializer,
    PaymentCreateSerializer,
    PaymentMethodSerializer,
    PaymentRefundSerializer,
    PaymentSerializer,
    ShiftCloseSerializer,
    ShiftCreateSerializer,
    ShiftSerializer,
)
from apps.finance.services import close_shift, refund_payment

class ManagerAPIView(generics.GenericAPIView):
    authentication_classes = [BasicAuthentication, SessionAuthentication]
    permission_classes = [IsAdminUser]


class ManagerListCreateView(ManagerAPIView, generics.ListCreateAPIView):
    create_serializer_class = None

    def get_serializer_class(self):
        if self.request.method == "POST":
            return self.create_serializer_class
        return self.serializer_class

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj = serializer.save(**self.get_extra_save_data())
        return Response(self.serializer_class(obj).data, status=status.HTTP_201_CREATED)

    def get_extra_save_data(self):
        return {}


class PaymentMethodListView(ManagerAPIView, generics.ListAPIView):
    queryset = PaymentMethod.objects.filter(deleted_at__isnull=True, is_active=True)
    serializer_class = PaymentMethodSerializer


class ShiftListCreateView(ManagerListCreateView):
    queryset = Shift.objects.filter(deleted_at__isnull=True).order_by("-opened_at")
    serializer_class = ShiftSerializer
    create_serializer_class = ShiftCreateSerializer

    def get_extra_save_data(self):
        return {"cashier": self.request.user}


class ShiftDetailView(ManagerAPIView, generics.RetrieveAPIView):
    queryset = Shift.objects.filter(deleted_at__isnull=True)
    serializer_class = ShiftSerializer


class PaymentListCreateView(ManagerListCreateView):
    queryset = Payment.objects.filter(deleted_at__isnull=True).order_by("-created_at")
    serializer_class = PaymentSerializer
    create_serializer_class = PaymentCreateSerializer


class ExpenseListCreateView(ManagerListCreateView):
    queryset = Expense.objects.filter(deleted_at__isnull=True).order_by("-created_at")
    serializer_class = ExpenseSerializer
    create_serializer_class = ExpenseCreateSerializer


class DailyReportListView(ManagerAPIView, generics.ListAPIView):
    serializer_class = DailyReportSerializer

    def get_queryset(self) -> QuerySet[DailyReport]:
        filters = DailyReportFilterSerializer(data=self.request.query_params)
        filters.is_valid(raise_exception=True)
        return DailyReport.objects.filter(
            deleted_at__isnull=True,
            **filters.validated_data,
        ).order_by("-date")


class ShiftCloseView(ManagerAPIView):
    queryset = Shift.objects.filter(deleted_at__isnull=True)
    serializer_class = ShiftCloseSerializer

    def post(self, request, *args, **kwargs):
        shift = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if shift.status != Shift.Status.OPEN:
            return Response(
                {"detail": "This shift is already closed."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if shift.payments.filter(status=Payment.Status.PENDING, deleted_at__isnull=True).exists():
            return Response(
                {"detail": "Some payments are still pending. Finish them first."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        close_shift(shift, serializer.validated_data["closing"])
        return Response(ShiftSerializer(shift).data)


class PaymentRefundView(ManagerAPIView):
    queryset = Payment.objects.filter(deleted_at__isnull=True)
    serializer_class = PaymentRefundSerializer

    def post(self, request, *args, **kwargs):
        payment = self.get_object()

        if payment.status != Payment.Status.PAID:
            return Response(
                {"detail": "Only paid payments can be refunded."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        refund_payment(payment)
        return Response(PaymentSerializer(payment).data)