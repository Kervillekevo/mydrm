from django.urls import path, include
from .import views
from .views import LoginView, RegisterView, LogoutView, ProfileDetailView
from django.http import HttpResponse

def home(request):
    return HttpResponse("Welcome to my Project Home page")

urlpatterns = [
    path('', home, name='home'),
    path('login/', LoginView.as_view(), name='LoginView'),
    path('register/', RegisterView.as_view(), name='RegisterView'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('profile/', ProfileDetailView.as_view(), name='profiledetailview')
]