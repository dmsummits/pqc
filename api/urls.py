from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserViewSet,
    ProductCategoryViewSet,
    TaskViewSet,
    SubTaskViewSet,
    ProductSerialViewSet,
    UserLoginAPIView,
    SubTasksBySerial,          # ✅ include this
    SubTaskStatusUpdateView
)

# ------------------------------
# ROUTER REGISTRATION
# ------------------------------
router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'categories', ProductCategoryViewSet)
router.register(r'tasks', TaskViewSet)
router.register(r'subtasks', SubTaskViewSet)
router.register(r'product-serials', ProductSerialViewSet)

urlpatterns = [
    path('', include(router.urls)),  # keep this as is
    path('login/', UserLoginAPIView.as_view(), name='user-login'),
    path('subtask-status-update/', SubTaskStatusUpdateView.as_view(), name='subtask-status-update'),

    # ✅ Add this line
    path('subtasks-by-serial/', SubTasksBySerial.as_view(), name='subtasks-by-serial'),
]
