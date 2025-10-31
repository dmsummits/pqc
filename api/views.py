from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from django.contrib.auth import authenticate, login
from django.utils import timezone
from django.db import transaction


from .models import (
    User,
    ProductCategory,
    Task,
    SubTask,
    ProductSerial,
    SerialSubTaskStatus  # ✅ new model for serial-based subtask status
)
from .serializers import (
    UserSerializer,
    UserLoginSerializer,
    ProductCategorySerializer,
    TaskSerializer,
    SubTaskSerializer,
    ProductSerialSerializer,
    SerialSubTaskStatusSerializer  # ✅ new serializer
)


# ------------------------------
# USER VIEWSET
# ------------------------------
class UserViewSet(viewsets.ModelViewSet):
    """CRUD operations for Users"""
    queryset = User.objects.all()
    serializer_class = UserSerializer


# ------------------------------
# PRODUCT CATEGORY VIEWSET
# ------------------------------
class ProductCategoryViewSet(viewsets.ModelViewSet):
    """CRUD operations for Product Categories (with nested tasks & subtasks)"""
    queryset = ProductCategory.objects.all()
    serializer_class = ProductCategorySerializer


# ------------------------------
# TASK VIEWSET
# ------------------------------
class TaskViewSet(viewsets.ModelViewSet):
    """CRUD operations for Tasks (linked to Product Categories)"""
    queryset = Task.objects.all()
    serializer_class = TaskSerializer


# ------------------------------
# SUBTASK VIEWSET
# ------------------------------
class SubTaskViewSet(viewsets.ModelViewSet):
    """CRUD operations for SubTasks"""
    queryset = SubTask.objects.all()
    serializer_class = SubTaskSerializer

    # ✅ Update only the status of a subtask
    @action(detail=True, methods=['post'], url_path='update-status')
    def update_status(self, request, pk=None):
        subtask = self.get_object()
        new_status = request.data.get('status')

        allowed_statuses = ['pending', 'OK', 'Not_OK']
        if new_status not in allowed_statuses:
            return Response(
                {'error': f"Invalid status. Allowed: {allowed_statuses}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        subtask.status = new_status
        subtask.save()

        return Response({
            'message': 'Status updated successfully',
            'subtask': SubTaskSerializer(subtask).data
        })

    # ✅ Get all subtasks for a given task
    @action(detail=False, methods=['get'], url_path='by-task')
    def by_task(self, request):
        task_id = request.query_params.get("task_id")
        if not task_id:
            return Response(
                {"error": "task_id query param is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            task = Task.objects.get(id=task_id)
        except Task.DoesNotExist:
            return Response({"error": "Task not found"}, status=status.HTTP_404_NOT_FOUND)

        subtasks = SubTaskSerializer(task.subtasks.all(), many=True).data
        return Response({
            "task_id": task.id,
            "task_name": task.name,
            "subtasks": subtasks
        })


# ------------------------------
# PRODUCT SERIAL VIEWSET
# ------------------------------
class ProductSerialViewSet(viewsets.ModelViewSet):
    """CRUD operations for Product Serials"""
    queryset = ProductSerial.objects.all()
    serializer_class = ProductSerialSerializer

    def create(self, request, *args, **kwargs):
        """Prevent duplicate serial_no"""
        serial_no = request.data.get('serial_no')
        if ProductSerial.objects.filter(serial_no=serial_no).exists():
            return Response(
                {"error": f"Serial number '{serial_no}' already exists."},
                status=status.HTTP_400_BAD_REQUEST
            )
        return super().create(request, *args, **kwargs)

    @action(detail=False, methods=['get'], url_path='by-product')
    def by_product(self, request):
        """Get all product serials for a given product_id"""
        product_id = request.query_params.get("product_id")
        if not product_id:
            return Response(
                {"error": "product_id query param is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        serials = ProductSerial.objects.filter(product_id=product_id)
        serializer = ProductSerialSerializer(serials, many=True)
        return Response(serializer.data)


class SubTasksBySerial(APIView):
    
    # -------------------------------
    # GET: Fetch all subtasks linked to a serial
    # -------------------------------
    def get(self, request):
        serial_number = request.query_params.get('serial_number')
        if not serial_number:
            return Response({"error": "serial_number is required"}, status=400)

        try:
            product_serial = ProductSerial.objects.get(serial_no=serial_number)
        except ProductSerial.DoesNotExist:
            return Response({"error": "Product Serial not found"}, status=404)

        # Get all subtasks linked to the same category as the serial’s product
        subtasks = SubTask.objects.filter(task__category=product_serial.product)

        # Ensure status rows exist for this serial & subtasks
        for s in subtasks:
            SerialSubTaskStatus.objects.get_or_create(
                product_serial=product_serial, subtask=s
            )

            # Re-fetch all statuses after updates
        serial_statuses = SerialSubTaskStatus.objects.filter(product_serial=product_serial)
        data = SerialSubTaskStatusSerializer(serial_statuses, many=True).data

        return Response({
             "product_serial": {
        "serial_no": product_serial.serial_no,
        "product_name": product_serial.product_name,
        "category": product_serial.product.name,
        "status": product_serial.status,
    },
    "subtask_statuses": data,
    "message": f"Fetched subtasks for {serial_number}",
        })

    # -------------------------------
    # POST: Update subtask statuses per serial
    # -------------------------------
    def post(self, request):
        serial_no = request.data.get("serial_no")
        updates = request.data.get("updates", [])

        if not serial_no or not updates:
            return Response({"error": "Missing data"}, status=400)

        try:
            product_serial = ProductSerial.objects.get(serial_no=serial_no)
        except ProductSerial.DoesNotExist:
            return Response({"error": "Product Serial not found"}, status=404)

        updated = []
        for item in updates:
            subtask_id = item.get("subtask_id")
            value = item.get("value")

            try:
                record = SerialSubTaskStatus.objects.get(
                    product_serial=product_serial, subtask_id=subtask_id
                )
                record.status = value
                record.save()
                updated.append({"subtask_id": subtask_id, "status": value})
            except SerialSubTaskStatus.DoesNotExist:
                continue

        return Response({
            "message": f"Updated subtasks for {serial_no}",
            "updated": updated
        })
# ------------------------------
# USER LOGIN API
# ------------------------------
class UserLoginAPIView(APIView):
    """User login with email and password"""
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        return Response({
            "message": "Login successful",
            "user": {
                "id": user.id,
                "name": user.name,
                "designation": user.designation,
                "email": user.email
            }
        }, status=status.HTTP_200_OK)
        
class SubTaskStatusUpdateView(APIView):
    """
    API to update multiple SerialSubTaskStatus records for a given product serial.
    """
    def post(self, request):
        serial_no = request.data.get("serial_no")
        updates = request.data.get("updates", [])

        if not serial_no or not updates:
            return Response({"error": "Missing serial_no or updates"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            product_serial = ProductSerial.objects.get(serial_no=serial_no)
        except ProductSerial.DoesNotExist:
            return Response({"error": f"Product serial '{serial_no}' not found"}, status=status.HTTP_404_NOT_FOUND)

        updated_count = 0
        errors = []

        with transaction.atomic():
            for u in updates:
                serial_status_id = u.get("id")
                new_status = u.get("status")
                updated_by = u.get("updated_by")  # received from Flutter
                remark = u.get("remark")  # ✅ new optional remark field

                if not serial_status_id or not new_status:
                    errors.append({"id": serial_status_id, "error": "Missing id or status"})
                    continue

                try:
                    sts = SerialSubTaskStatus.objects.get(id=serial_status_id)
                except SerialSubTaskStatus.DoesNotExist:
                    errors.append({"id": serial_status_id, "error": "Not found"})
                    continue

                if sts.product_serial.serial_no != serial_no:
                    errors.append({"id": serial_status_id, "error": "Serial number mismatch"})
                    continue

                # ✅ Pass updated_by to serializer
                serializer = SerialSubTaskStatusSerializer(
                    sts,
                    data={
                        "status": new_status,
                        "updated_by": updated_by,
                        "remark": remark
                    },
                    partial=True,
                    context={'request': request}
                )

                if serializer.is_valid():
                    serializer.save()
                    updated_count += 1
                else:
                    errors.append({"id": serial_status_id, "error": serializer.errors})

        return Response({
            "updated_count": updated_count,
            "errors": errors,
            "message": "Status update completed"
        }, status=status.HTTP_200_OK)