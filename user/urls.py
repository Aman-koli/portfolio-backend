from django.urls import path
from .views import signup, login, forgot_password, reset_password, change_password, publish_portfolio, get_portfolio,create_order, verify_payment

urlpatterns = [
    path("signup/", signup),
    path("login/", login),
    path("forgot-password/", forgot_password),
    path("reset-password/", reset_password),
    path("change-password/", change_password),
    path("portfolio/publish/", publish_portfolio),
    path("portfolio/<slug:slug>/", get_portfolio),
    path("api/portfolio/<str:slug>/", get_portfolio),
    path('create-order/', create_order),
    path('verify-payment/', verify_payment),
    
]