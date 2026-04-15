from django.urls import path
from . import views

urlpatterns = [
    path('', views.index),

    path('login', views.login_view),
    path('logout', views.logout_view),

    path('free-times', views.free_times),

    path('tickets/create', views.create_ticket),
    path('my/tickets', views.my_tickets),
    path('tickets/<int:id>/cancel', views.cancel_ticket),

    path('admin', views.admin_dashboard),
    path('admin/tickets', views.admin_tickets),
    path('admin/tickets/<int:id>/status', views.update_ticket_status),

    path('admin/services', views.admin_services),
    path('admin/services/new', views.create_service),
    path('admin/services/<int:id>/edit', views.edit_service),
    path('admin/services/<int:id>/delete', views.delete_service),
]