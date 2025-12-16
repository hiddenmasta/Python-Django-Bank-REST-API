
from django.urls import path
from . import views

urlpatterns = [
    # /users/ [GET, POST]
    path('users/', views.users_collection),
    # /users/<id>/ [PUT]
    path('users/<uuid:id>/', views.user_detail),
    # /accounts/ [GET, POST]
    path('accounts/', views.accounts_collection),
    # /accounts/<int:id>/transfer/ [PATCH]
    path('accounts/<uuid:id>/transfer/', views.transfer_money_to_account),
    # /transfers/ [POST]
    path('transfers/', views.transfer_money_between_accounts),
]