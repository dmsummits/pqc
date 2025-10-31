from django.db import models

# ------------------------------
# User
# ------------------------------
class User(models.Model):
    name = models.CharField(max_length=100)
    designation = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=100)

    def __str__(self):
        return self.name


# ------------------------------
# Product Category
# ------------------------------
class ProductCategory(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


# ------------------------------
# Task
# ------------------------------
class Task(models.Model):
    category = models.ForeignKey(ProductCategory, on_delete=models.CASCADE, related_name='tasks')
    name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.name} ({self.category.name})"


# ------------------------------
# SubTask
# ------------------------------
class SubTask(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
    ]

    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='subtasks')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')

    def __str__(self):
        return f"{self.name} ({self.task.name})"


# ------------------------------
# Product Serial
# ------------------------------
class ProductSerial(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
    ]

    serial_no = models.CharField(max_length=50, primary_key=True)
    product = models.ForeignKey(ProductCategory, on_delete=models.CASCADE, related_name='product_serials')
    product_name = models.CharField(max_length=100)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    subtask = models.ForeignKey(SubTask, on_delete=models.CASCADE, related_name='product_serials', null=True, blank=True)

    def __str__(self):
        return f"{self.serial_no} - {self.product.name} - {self.status}"


# ------------------------------
# SerialSubTaskStatus
# ------------------------------
class SerialSubTaskStatus(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('OK', 'OK'),
        ('Not_OK', 'Not OK'),
    ]

    product_serial = models.ForeignKey(ProductSerial, on_delete=models.CASCADE, related_name='serial_subtasks')
    subtask = models.ForeignKey(SubTask, on_delete=models.CASCADE, related_name='serial_statuses')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
  # 👇 New fields
    remark = models.TextField(null=True, blank=True)  # ✅ Added field for remarks
    updated_by = models.CharField(max_length=150, null=True, blank=True)
    update_time = models.DateTimeField(null=True, blank=True)
    class Meta:
        unique_together = ('product_serial', 'subtask')

    def __str__(self):
        return f"{self.product_serial.serial_no} - {self.subtask.name}: {self.status}"
