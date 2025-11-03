from django.urls import path
from . import views

urlpatterns = [
    path('users', views.list_users),
    path('users/create/', views.create_user),
    path('users/<int:id>/update/', views.update_user),
    path('accounts', views.list_accounts),
    path('users/<int:user_id>/account/create/', views.create_account),
    path('users/<int:user_id>/accounts/<int:account_id>/transfer/', views.transfer_money_to_account),
    path('accounts/transfer/', views.transfer_money_between_accounts)
]