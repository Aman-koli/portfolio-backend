from django.db import models

class User(models.Model):
    username = models.CharField(max_length=100, unique=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255)
    plan = models.CharField(max_length=50,default="free")
    created_at = models.DateTimeField(auto_now_add=True)


    reset_token = models.CharField(max_length=100, blank=True, null=True)

    # Avatar/profile picture
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    
    def __str__(self):
        return self.username



class Portfolio(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="portfolios")
    slug = models.SlugField(max_length=150, unique=True)
    template = models.CharField(max_length=50, default="minimal")
    portfolio_data = models.JSONField(default=dict)
    published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.slug}"       