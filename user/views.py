from django.contrib.auth import logout as dj_logout
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.core.mail import send_mail
from django.conf import settings
import json
import uuid
from datetime import datetime, timedelta
from .models import User, Portfolio
from django.contrib.auth.hashers import make_password, check_password
import razorpay

# ✅ SIRF EK BAAR - Real keys
razorpay_client = razorpay.Client(
    auth=("rzp_live_SYYztqlyCAwMbt", "uWir5e211IOOmQiWIvBw5qFp")
)

reset_tokens = {}


# ---------------- SIGNUP ---------------- #
@csrf_exempt
def signup(request):
    if request.method == "POST":
        data = json.loads(request.body)
        username = data.get("username", "").strip()
        email = data.get("email", "").strip().lower()
        password = data.get("password", "")

        if not username or not email or not password:
            return JsonResponse({"error": "All fields are required"}, status=400)
        if len(password) < 6:
            return JsonResponse({"error": "Password must be at least 6 characters"}, status=400)
        if User.objects.filter(username=username).exists():
            return JsonResponse({"error": "Username already exists"}, status=400)
        if User.objects.filter(email=email).exists():
            return JsonResponse({"error": "Email already exists"}, status=400)

        User.objects.create(
            username=username,
            email=email,
            password=make_password(password)
        )
        return JsonResponse({"message": "Signup successful"}, status=201)

    return JsonResponse({"error": "Only POST request allowed"}, status=405)


# ---------------- LOGIN ---------------- #
@csrf_exempt
def login(request):
    if request.method == "POST":
        data = json.loads(request.body)
        email = data.get("email", "").lower()
        password = data.get("password", "")

        try:
            user = User.objects.get(email=email)
            if check_password(password, user.password):
                return JsonResponse({
                    "message": "Login successful",
                    "username": user.username,
                    "email": user.email,
                    "plan": getattr(user, "plan", "free"),
                })
            else:
                return JsonResponse({"error": "Wrong password"}, status=400)
        except User.DoesNotExist:
            return JsonResponse({"error": "User not found"}, status=404)

    return JsonResponse({"error": "Only POST request allowed"}, status=405)


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
        email = data.get("email", "").lower()

        if not email:
            return JsonResponse({"error": "Email is required"}, status=400)

        try:
            user = User.objects.get(email=email)
            token = str(uuid.uuid4())
            reset_tokens[token] = {
                "email": email,
                "expires": datetime.now() + timedelta(minutes=10)
            }

            reset_link = f"http://localhost:5173/reset-password/{token}"
            send_mail(
                subject="Password Reset Request",
                message=f"""Hello {user.username},\n\nPassword reset ke liye niche link pe click karo:\n\n{reset_link}\n\nYe link 10 minute ke liye valid hai.\n\nAgar tumne request nahi ki, ignore karo.""",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
            return JsonResponse({"message": "Reset link sent"}, status=200)

        except User.DoesNotExist:
            return JsonResponse({"error": "User not found"}, status=404)

    return JsonResponse({"error": "Only POST request allowed"}, status=405)


# ---------------- RESET PASSWORD ---------------- #
@csrf_exempt
def reset_password(request):
    if request.method == "POST":
        data = json.loads(request.body)
        token = data.get("token")
        new_password = data.get("new_password")

        if not token or not new_password:
            return JsonResponse({"error": "Token and password required"}, status=400)

        token_data = reset_tokens.get(token)
        if not token_data:
            return JsonResponse({"error": "Invalid token"}, status=400)

        if datetime.now() > token_data["expires"]:
            reset_tokens.pop(token)
            return JsonResponse({"error": "Token expired"}, status=400)

        try:
            user = User.objects.get(email=token_data["email"])
            user.password = make_password(new_password)
            user.save()
            reset_tokens.pop(token)
            return JsonResponse({"message": "Password reset successful"})
        except User.DoesNotExist:
            return JsonResponse({"error": "User not found"}, status=404)

    return JsonResponse({"error": "Only POST request allowed"}, status=405)


# ---------------- CHANGE PASSWORD ---------------- #
@csrf_exempt
def change_password(request):
    if request.method == "POST":
        data = json.loads(request.body)
        email = data.get("email", "").lower()
        old_password = data.get("old_password")
        new_password = data.get("new_password")

        if not email or not old_password or not new_password:
            return JsonResponse({"error": "All fields required"}, status=400)

        try:
            user = User.objects.get(email=email)
            if check_password(old_password, user.password):
                user.password = make_password(new_password)
                user.save()
                return JsonResponse({"message": "Password changed"})
            else:
                return JsonResponse({"error": "Wrong old password"}, status=400)
        except User.DoesNotExist:
            return JsonResponse({"error": "User not found"}, status=404)

    return JsonResponse({"error": "Only POST request allowed"}, status=405)


# ---------------- PUBLISH PORTFOLIO ---------------- #
@csrf_exempt
def publish_portfolio(request):
    if request.method == "POST":
        data = json.loads(request.body)
        email = data.get("email", "").lower()
        template = data.get("template", "minimal")
        portfolio_data = data.get("portfolioData", {})
        name = portfolio_data.get("name", "user")

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return JsonResponse({"error": "User not found"}, status=404)

        base_slug = name.lower().strip().replace(" ", "-")
        slug = base_slug

        while Portfolio.objects.filter(slug=slug).exclude(user=user).exists():
            slug = f"{base_slug}-{uuid.uuid4().hex[:4]}"

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
            "message": "Portfolio published",
            "slug": slug,
            "url": f"http://localhost:5173/p/{slug}"
        })

    return JsonResponse({"error": "Only POST request allowed"}, status=405)


# ---------------- GET PORTFOLIO ---------------- #
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


# ---------------- CREATE ORDER ---------------- #
@csrf_exempt
def create_order(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            amount = data.get("amount")

            if not amount:
                return JsonResponse({"error": "Amount required"}, status=400)

            order = razorpay_client.order.create({
                "amount": int(amount),
                "currency": "INR",
                "payment_capture": 1
            })

            print("ORDER CREATED:", order)
            return JsonResponse(order)

        except Exception as e:
            print("CREATE ORDER ERROR:", e)
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request"}, status=400)


# ---------------- VERIFY PAYMENT ---------------- #
@csrf_exempt
def verify_payment(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)

            params_dict = {
                'razorpay_order_id': data.get('razorpay_order_id'),
                'razorpay_payment_id': data.get('razorpay_payment_id'),
                'razorpay_signature': data.get('razorpay_signature')
            }

            razorpay_client.utility.verify_payment_signature(params_dict)

            return JsonResponse({"status": "success"})

        except Exception as e:
            print("VERIFY ERROR:", e)
            return JsonResponse({"status": "failed"})

    return JsonResponse({"error": "Invalid request"}, status=400)