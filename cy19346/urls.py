from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path

from cy19346_project import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("", views.dashboard, name="dashboard"),
    path("sync/ozon/", views.sync_ozon, name="sync_ozon"),
    path("stocks/own/", views.save_own_stock, name="save_own_stock"),
    path("stocks/own/<int:pk>/delete/", views.delete_own_stock, name="delete_own_stock"),
]
