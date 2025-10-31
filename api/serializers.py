from rest_framework import serializers
from django.utils import timezone
from .models import (
    User,
    ProductCategory,
    Task,
    SubTask,
    ProductSerial,
    SerialSubTaskStatus
)

# ------------------------------
# ✅ User Serializer
# ------------------------------
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = '__all__'


# ------------------------------
# ✅ User Login Serializer
# ------------------------------
class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        email = data.get("email")
        password = data.get("password")

        try:
            user = User.objects.get(email=email, password=password)
        except User.DoesNotExist:
            raise serializers.ValidationError("Invalid email or password")

        data["user"] = user
        return data


# ------------------------------
# ✅ Product Serial Serializer
# ------------------------------
class ProductSerialSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    subtask_name = serializers.CharField(source='subtask.name', read_only=True)

    class Meta:
        model = ProductSerial
        fields = [
            'serial_no',
            'product',
            'product_name',
            'status',
            'subtask',
            'subtask_name'
        ]
        read_only_fields = ['product_name', 'subtask_name']


# ------------------------------
# ✅ SubTask Serializer (with linked product serials)
# ------------------------------
class SubTaskSerializer(serializers.ModelSerializer):
    task_name = serializers.CharField(source='task.name', read_only=True)
    product_serials = serializers.SerializerMethodField()

    class Meta:
        model = SubTask
        fields = [
            'id',
            'name',
            'description',
            'task',
            'task_name',
            'status',
            'product_serials'
        ]
        read_only_fields = ['id', 'task_name', 'product_serials']

    def get_product_serials(self, obj):
        """Return all product serials linked to this subtask"""
        serials = obj.product_serials.all()
        return ProductSerialSerializer(serials, many=True).data


# ------------------------------
# ✅ Task Serializer (nested subtasks)
# ------------------------------
class TaskSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    subtasks = SubTaskSerializer(many=True, read_only=True)

    class Meta:
        model = Task
        fields = ['id', 'name', 'category', 'category_name', 'subtasks']
        read_only_fields = ['id', 'category_name', 'subtasks']


# ------------------------------
# ✅ Product Category Serializer (nested tasks)
# ------------------------------
class ProductCategorySerializer(serializers.ModelSerializer):
    tasks = TaskSerializer(many=True, read_only=True)

    class Meta:
        model = ProductCategory
        fields = ['id', 'name', 'description', 'tasks']
        read_only_fields = ['id', 'tasks']


class SerialSubTaskStatusSerializer(serializers.ModelSerializer):
    subtask_name = serializers.CharField(source='subtask.name', read_only=True)
    task_id = serializers.IntegerField(source='subtask.task.id', read_only=True)
    task_name = serializers.CharField(source='subtask.task.name', read_only=True)
    serial_no = serializers.CharField(source='product_serial.serial_no', read_only=True)
    product_name = serializers.CharField(source='product_serial.product.name', read_only=True)
    
    # Editable fields
    updated_by = serializers.CharField(required=False)
    remark = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    
    update_time = serializers.DateTimeField(read_only=True)

    class Meta:
        model = SerialSubTaskStatus
        fields = [
            'id',
            'serial_no',
            'product_name',
            'task_id',
            'task_name',
            'subtask',
            'subtask_name',
            'status',
            'updated_by',
            'remark',
            'update_time'
        ]
        read_only_fields = [
            'id',
            'serial_no',
            'product_name',
            'task_id',
            'task_name',
            'subtask_name',
            'update_time'
        ]

    def validate_status(self, value):
        allowed = ["pending", "OK", "Not_OK"]
        if value not in allowed:
            raise serializers.ValidationError(f"Status must be one of {allowed}")
        return value

    def update(self, instance, validated_data):
        instance.status = validated_data.get('status', instance.status)
        instance.remark = validated_data.get('remark', instance.remark)

        # ✅ Use Flutter value if provided, else request.user, else "Unknown"
        request = self.context.get('request')
        if 'updated_by' in validated_data and validated_data['updated_by']:
            instance.updated_by = validated_data['updated_by']
        elif request and hasattr(request, 'user') and request.user.is_authenticated:
            instance.updated_by = getattr(request.user, 'name', None) or getattr(request.user, 'username', 'Unknown')
        else:
            instance.updated_by = "Unknown"

        instance.update_time = timezone.now()
        instance.save()
        return instance
