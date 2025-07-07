from django.urls import path, include
from .import views
from .views import LoginView, RegisterView, LogoutView, ProfileDetailView, RequestPasswordResetEmail, PasswordTokenCheckAPI, PasswordResetConfirm
from django.http import HttpResponse

def home(request):
    return HttpResponse("Welcome to my Project Home page")

urlpatterns = [
    path('', home, name='home'),
    path('login/', LoginView.as_view(), name='LoginView'),
    path('register/', RegisterView.as_view(), name='RegisterView'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('profile/', ProfileDetailView.as_view(), name='profiledetailview'),
    path('password-reset/', RequestPasswordResetEmail.as_view(), name='password-reset'),
    path('password-reset-check/<uidb64>/<token>/', PasswordTokenCheckAPI.as_view(), name='password-reset-check'),
    path('password-reset-confirm/<uidb64>/<token>/', PasswordResetConfirm.as_view(), name='password-reset-confirm'),
]