from django.shortcuts import render, redirect
from django.http import JsonResponse
from .models import User, Service, Ticket
from datetime import datetime, timedelta, time as dtime

STEP_MINUTES = 10
LEAD_MINUTES = 30

WORK_START = dtime(8, 0)
WORK_END_LAST_SLOT = dtime(16, 50)
DAYS_AHEAD = 14

BLOCKING_STATUSES = {"waiting", "approved", "served", "no_show"}


def get_user(request):
    uid = request.session.get("user_id")
    if not uid:
        return None
    return User.objects.filter(id=uid).first()


def build_dates():
    dates = []
    now = datetime.now()
    today = now.date()

    for i in range(DAYS_AHEAD):
        d = today + timedelta(days=i)

        if d.weekday() in (5, 6):
            continue

        if d == today and now.time() > WORK_END_LAST_SLOT:
            continue

        dates.append(d.strftime("%Y-%m-%d"))

    return dates


def build_all_times():
    times = []
    h, m = WORK_START.hour, WORK_START.minute

    while True:
        times.append(f"{h:02d}:{m:02d}")

        m += STEP_MINUTES
        if m >= 60:
            h += 1
            m -= 60

        if h > WORK_END_LAST_SLOT.hour or (h == WORK_END_LAST_SLOT.hour and m > WORK_END_LAST_SLOT.minute):
            break

    return times


def build_free_times(date_str):
    all_times = build_all_times()

    day_start = datetime.strptime(f"{date_str} 00:00", "%Y-%m-%d %H:%M")
    day_end = day_start + timedelta(days=1)

    tickets = Ticket.objects.filter(
        scheduled_for__gte=day_start,
        scheduled_for__lt=day_end,
        status__in=BLOCKING_STATUSES
    )

    booked = {t.scheduled_for.strftime("%H:%M") for t in tickets}
    free_times = [t for t in all_times if t not in booked]

    now = datetime.now()
    lead_cutoff = now + timedelta(minutes=LEAD_MINUTES)
    today_str = now.strftime("%Y-%m-%d")

    if date_str == today_str:
        free_times = [
            t for t in free_times
            if datetime.strptime(f"{date_str} {t}", "%Y-%m-%d %H:%M") >= lead_cutoff
        ]

    return free_times


def login_view(request):
    if request.method == "POST":
        user = User.objects.filter(
            username=request.POST.get("username"),
            password=request.POST.get("password")
        ).first()

        if user:
            request.session["user_id"] = user.id
            return redirect("/admin" if user.role == "admin" else "/")

        return render(request, "login.html", {"error": "Невірні дані"})

    return render(request, "login.html")


def logout_view(request):
    request.session.flush()
    return redirect("/login")


def index(request):
    user = get_user(request)
    if not user:
        return redirect("/login")

    if user.role == "admin":
        return redirect("/admin")

    services = Service.objects.filter(is_active=True)
    dates = build_dates()
    selected_date = dates[0] if dates else None
    times = build_free_times(selected_date) if selected_date else []

    return render(request, "index.html", {
        "user": user,
        "services": services,
        "dates": dates,
        "times": times
    })


def free_times(request):
    date = request.GET.get("date")

    if date not in build_dates():
        return JsonResponse({"times": []})

    return JsonResponse({"times": build_free_times(date)})


def create_ticket(request):
    user = get_user(request)
    if not user or user.role != "user":
        return redirect("/login")

    if request.method == "POST":
        service_id = int(request.POST.get("service_id"))
        date = request.POST.get("date")
        time = request.POST.get("time")

        services = Service.objects.filter(is_active=True)
        if not any(s.id == service_id for s in services):
            return render(request, "index.html", {"error": "Невірна послуга"})

        if date not in build_dates():
            return render(request, "index.html", {"error": "Невірна дата"})

        try:
            scheduled = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
        except:
            return render(request, "index.html", {"error": "Невірний формат"})

        now = datetime.now()
        if scheduled < now + timedelta(minutes=LEAD_MINUTES):
            return render(request, "index.html", {"error": "Мінімум за 30 хв"})

        if not (WORK_START <= scheduled.time() <= WORK_END_LAST_SLOT):
            return render(request, "index.html", {"error": "Поза робочим часом"})

        if scheduled.minute % STEP_MINUTES != 0:
            return render(request, "index.html", {"error": "Крок 10 хв"})

        conflict = Ticket.objects.filter(
            scheduled_for=scheduled,
            status__in=BLOCKING_STATUSES
        ).first()

        if conflict:
            return render(request, "index.html", {"error": "Час зайнятий"})

        ticket_number = f"A{int(datetime.now().timestamp())}"

        Ticket.objects.create(
            user=user,
            service_id=service_id,
            scheduled_for=scheduled,
            ticket_number=ticket_number,
            status="waiting"
        )

    return redirect("/my/tickets")


def my_tickets(request):
    user = get_user(request)
    if not user or user.role != "user":
        return redirect("/login")

    tickets = Ticket.objects.filter(user=user).order_by("-scheduled_for")

    return render(request, "my_tickets.html", {
        "tickets": tickets,
        "user": user
    })


def cancel_ticket(request, id):
    user = get_user(request)
    if not user or user.role != "user":
        return redirect("/login")

    t = Ticket.objects.get(id=id)

    if t.status in {"waiting", "approved"}:
        t.status = "canceled"
        t.canceled_by = "user"
        t.save()

    return redirect("/my/tickets")



def admin_dashboard(request):
    user = get_user(request)
    if not user or user.role != "admin":
        return redirect("/login")

    return render(request, "admin_dashboard.html", {
        "user": user,
        "waiting": Ticket.objects.filter(status="waiting").count(),
        "services": Service.objects.all()
    })


def admin_tickets(request):
    user = get_user(request)
    if not user or user.role != "admin":
        return redirect("/login")

    return render(request, "admin_tickets.html", {
        "user": user,
        "tickets": Ticket.objects.all().order_by("scheduled_for")
    })


def update_ticket_status(request, id):
    user = get_user(request)
    if not user or user.role != "admin":
        return redirect("/login")

    if request.method == "POST":
        status = request.POST.get("status")
        t = Ticket.objects.get(id=id)

        if t.status not in {"served", "no_show", "canceled"}:
            t.status = status
            if status == "canceled":
                t.canceled_by = "admin"
            t.save()

    return redirect("/admin/tickets")


def admin_services(request):
    user = get_user(request)
    if not user or user.role != "admin":
        return redirect("/login")

    return render(request, "services_list.html", {
        "user": user,
        "services": Service.objects.all()
    })


def create_service(request):
    user = get_user(request)

    if not user or user.role != "admin":
        return redirect("/login")

    if request.method == "GET":
        return render(request, "service_form.html", {
            "service": None,
            "user": user
        })

    if request.method == "POST":
        Service.objects.create(
            name=request.POST.get("name"),
            description=request.POST.get("description"),
            is_active=bool(request.POST.get("is_active"))
        )

        return redirect("/admin/services")


def edit_service(request, id):
    user = get_user(request)
    if not user or user.role != "admin":
        return redirect("/login")

    s = Service.objects.get(id=id)

    if request.method == "POST":
        s.name = request.POST.get("name")
        s.description = request.POST.get("description")
        s.is_active = bool(request.POST.get("is_active"))
        s.save()
        return redirect("/admin/services")

    return render(request, "service_form.html", {"service": s, "user": user})


def delete_service(request, id):
    user = get_user(request)
    if not user or user.role != "admin":
        return redirect("/login")

    Service.objects.get(id=id).delete()
    return redirect("/admin/services")