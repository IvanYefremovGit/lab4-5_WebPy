from django.db import models


class User(models.Model):
    ROLE_CHOICES = [
        ("user", "User"),
        ("admin", "Admin"),
    ]

    username = models.CharField(max_length=100, unique=True)
    password = models.CharField(max_length=100)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="user")

    def __str__(self):
        return self.username


class Service(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Ticket(models.Model):
    STATUS_CHOICES = [
        ("waiting", "Waiting"),
        ("approved", "Approved"),
        ("served", "Served"),
        ("no_show", "No Show"),
        ("canceled", "Canceled"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    service = models.ForeignKey(Service, on_delete=models.CASCADE)

    ticket_number = models.CharField(max_length=20)
    scheduled_for = models.DateTimeField()

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="waiting")
    canceled_by = models.CharField(max_length=20, null=True, blank=True)

    def __str__(self):
        return f"{self.user} - {self.service} - {self.status}"