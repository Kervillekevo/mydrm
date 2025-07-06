from django.shortcuts import render
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from .serializers import RegisterSerializer, ProfileSerializer
from rest_framework import generics, status, permissions
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.contrib.auth import logout
from rest_framework.permissions import IsAuthenticated
from .models import Profile
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import smart_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.conf import settings
from django.core.mail import send_mail
from rest_framework.response import Response
from rest_framework import generics, status
from .serializers import PasswordResetRequestSerializer, SetNewPasswordSerializer

# Create your views here.


class RegisterView(generics.GenericAPIView):
    serializer_class = RegisterSerializer

    def post(self, request):
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        

        token, created = Token.objects.get_or_create(user=user)
        return Response({
            'user':{
                'username':user.username,
                 'email':user.email
            },
            'token':token.key
        }, status=status.HTTP_201_CREATED)
    

class LoginView(APIView):
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        user = authenticate(username=username, password=password)

        if user:
            # ✅ Create or get existing token for the user
            token, created = Token.objects.get_or_create(user=user)

            return Response({
                'message': 'Login successful',
                'token': token.key,
                'username': user.username,
                'email': user.email
            }, status=status.HTTP_200_OK)

        return Response({'error': 'Invalid Credentials'}, status=status.HTTP_401_UNAUTHORIZED)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        request.user.auth_token.delete()
        return Response({"message": "Successfully logged out"}, status=status.HTTP_200_OK)
    

class ProfileDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        profile, created = Profile.objects.get_or_create(user=self.request.user)
        return profile    
    

class RequestPasswordResetEmail(generics.GenericAPIView):
    serializer_class = PasswordResetRequestSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']

        user = User.objects.filter(email=email).first()
        if user:
            uidb64 = urlsafe_base64_encode(smart_bytes(user.id))
            token = PasswordResetTokenGenerator().make_token(user)
            reset_url = f"http://localhost:8000/api/password-reset-confirm/?uidb64={uidb64}&token={token}"

            # Send email
            send_mail(
                subject='Password Reset Request',
                message=f'Click the link to reset your password: {reset_url}',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )

        return Response({'success': 'If your email exists, we sent a password reset link.'}, status=status.HTTP_200_OK)
class PasswordTokenCheckAPI(APIView):
    def get(self, request, uidb64, token):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response({'error': 'Invalid UID'}, status=status.HTTP_400_BAD_REQUEST)

        if not PasswordResetTokenGenerator().check_token(user, token):
            return Response({'error': 'The reset link is invalid or expired.'}, status=status.HTTP_400_BAD_REQUEST)

        return Response({'success': 'Token is valid', 'uidb64': uidb64, 'token': token}, status=status.HTTP_200_OK)


class PasswordResetConfirm(generics.GenericAPIView):
    serializer_class = SetNewPasswordSerializer

    def post(self, request):
        uidb64 = request.data.get('uidb64')
        token = request.data.get('token')
        password = request.data.get('password')

        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
            print("User found:", user.username)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response({'error': 'Invalid UID'}, status=status.HTTP_400_BAD_REQUEST)

        if not PasswordResetTokenGenerator().check_token(user, token):
            return Response({'error': 'The reset link is invalid or expired.'}, status=status.HTTP_400_BAD_REQUEST)

        print("Token is valid for user:", user.username)

        user.set_password(password)
        user.save()

        print("Password reset and saved!")

        return Response({'success': 'Password reset successful!'}, status=status.HTTP_200_OK)

