from django.contrib.auth import logout as dj_logout
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.core.mail import send_mail
from django.conf import settings
import json
import uuid
from .models import User, Portfolio
from django.contrib.auth.hashers import make_password, check_password

reset_tokens = {}


# ---------------- SIGNUP ---------------- #
@csrf_exempt
def signup(request):
    if request.method == "POST":
        data = json.loads(request.body)
        username = data.get("username", "").strip()
        email = data.get("email", "").strip()
        password = data.get("password", "")

        if not username or not email or not password:
            return JsonResponse({"error": "All fields are required"})

        if User.objects.filter(username=username).exists():
            return JsonResponse({"error": "Username already exists"})

        if User.objects.filter(email=email).exists():
            return JsonResponse({"error": "Email already exists"})

        hashed_password = make_password(password)
        User.objects.create(
            username=username,
            email=email,
            password=hashed_password
        )

        return JsonResponse({"message": "Signup successful"})

    return JsonResponse({"error": "Only POST request allowed"})


# ---------------- LOGIN ---------------- #
@csrf_exempt
def login(request):
    if request.method == "POST":
        data = json.loads(request.body)
        email = data.get("email")
        password = data.get("password")

        try:
            user = User.objects.get(email=email)
            if check_password(password, user.password):
                return JsonResponse({
                    "message": "Login successful",
                    "username": user.username,
                    "email": user.email,
                    "plan": user.plan,
                })
            else:
                return JsonResponse({"error": "Wrong password"})
        except User.DoesNotExist:
            return JsonResponse({"error": "User not found"})

    return JsonResponse({"error": "Only POST request allowed"})


# ---------------- LOGOUT ---------------- #
@csrf_exempt
def logout(request):
    dj_logout(request)
    return JsonResponse({"message": "Logged out successfully"})


# ---------------- FORGOT PASSWORD ---------------- #
@csrf_exempt
def forgot_password(request):
    if request.method == "POST":
        data = json.loads(request.body)
        email = data.get("email")

        if not email:
            return JsonResponse({"error": "Email is required"})

        try:
            user = User.objects.get(email=email)

            token = str(uuid.uuid4())
            reset_tokens[token] = email

            reset_link = f"http://localhost:5173/reset-password/{token}"

            send_mail(
                subject="Password Reset Request",
                message=f"""Hello {user.username},

Aapne password reset request ki hai.

Neeche diye link pe click karein:
{reset_link}

Yeh link sirf ek baar use ho sakta hai.

Agar aapne request nahi ki toh is email ko ignore karein.

Thanks""",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )

            return JsonResponse({"message": "Password reset link sent to your email!"})

        except User.DoesNotExist:
            return JsonResponse({"error": "User with this email does not exist"})

    return JsonResponse({"error": "Only POST request allowed"})


# ---------------- RESET PASSWORD ---------------- #
@csrf_exempt
def reset_password(request):
    if request.method == "POST":
        data = json.loads(request.body)
        token = data.get("token")
        new_password = data.get("new_password")

        if not token or not new_password:
            return JsonResponse({"error": "Token and new password are required"})

        email = reset_tokens.get(token)
        if not email:
            return JsonResponse({"error": "Invalid or expired token"})

        try:
            user = User.objects.get(email=email)
            user.password = make_password(new_password)
            user.save()
            reset_tokens.pop(token)
            return JsonResponse({"message": "Password reset successful"})
        except User.DoesNotExist:
            return JsonResponse({"error": "User not found"})

    return JsonResponse({"error": "Only POST request allowed"})


# ---------------- CHANGE PASSWORD ---------------- #
@csrf_exempt
def change_password(request):
    if request.method == "POST":
        data = json.loads(request.body)
        old_password = data.get("old_password")
        new_password = data.get("new_password")

        if not old_password or not new_password:
            return JsonResponse({"error": "Old and new password are required"})

        email = data.get("email")
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return JsonResponse({"error": "User not found"})

        if check_password(old_password, user.password):
            user.password = make_password(new_password)
            user.save()
            return JsonResponse({"message": "Password changed successfully"})
        else:
            return JsonResponse({"error": "Old password is incorrect"})

    return JsonResponse({"error": "Only POST request allowed"})


# ---------------- PUBLISH PORTFOLIO ---------------- #
@csrf_exempt
def publish_portfolio(request):
    if request.method == "POST":
        data = json.loads(request.body)
        email = data.get("email")
        template = data.get("template", "minimal")
        portfolio_data = data.get("portfolioData", {})
        name = portfolio_data.get("name", "user")

        # User dhundo
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return JsonResponse({"error": "User not found"}, status=404)

        # Slug banao — aman-khan
        base_slug = name.lower().strip().replace(" ", "-")
        slug = base_slug

        # Agar doosre user ka same slug ho toh unique banao
        existing = Portfolio.objects.filter(slug=slug).exclude(user=user).first()
        if existing:
            slug = f"{base_slug}-{uuid.uuid4().hex[:4]}"

        # Save ya update karo
        portfolio, created = Portfolio.objects.update_or_create(
            user=user,
            defaults={
                "slug": slug,
                "template": template,
                "portfolio_data": portfolio_data,
                "published": True,
            }
        )

        return JsonResponse({
            "message": "Portfolio published successfully!",
            "slug": portfolio.slug,
            "url": f"http://localhost:5173/p/{portfolio.slug}"
        })

    return JsonResponse({"error": "Only POST request allowed"})


# ---------------- GET PUBLIC PORTFOLIO ---------------- #
@csrf_exempt
def get_portfolio(request, slug):
    try:
        portfolio = Portfolio.objects.get(slug=slug, published=True)
        return JsonResponse({
            "slug": portfolio.slug,
            "template": portfolio.template,
            "portfolioData": portfolio.portfolio_data,
            "username": portfolio.user.username,
        })
    except Portfolio.DoesNotExist:
        return JsonResponse({"error": "Portfolio not found"}, status=404)