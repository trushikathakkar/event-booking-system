from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Event, Booking
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.contrib.auth.models import User

# 🔹 Event List (Home Page)
def event_list(request):
    search_query = request.GET.get('search', '')

    events = Event.objects.all()

    if search_query:
        events = events.filter(title__icontains=search_query)

    booking_count = 0
    if request.user.is_authenticated:
        booking_count = Booking.objects.filter(user=request.user).count()

    return render(request, "event_list.html", {
        "events": events,
        "booking_count": booking_count,
        "search_query": search_query
    })


# 🔹 Event Detail
@login_required(login_url='login')
def event_detail(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    return render(request, "event_detail.html", {"event": event})


# 🔹 Book Ticket (SAFE + ATOMIC)
@login_required(login_url='login')
def book_ticket(request, event_id):

    if request.method == "POST":

        quantity = request.POST.get('quantity')

        # validation
        if not quantity or not quantity.isdigit():
            messages.error(request, "Invalid quantity!")
            return redirect('event_detail', event_id=event_id)

        quantity = int(quantity)

        if quantity <= 0:
            messages.error(request, "Quantity must be greater than 0!")
            return redirect('event_detail', event_id=event_id)

        try:
            with transaction.atomic():

                event = Event.objects.select_for_update().get(id=event_id)

                if quantity > event.available_tickets:
                    messages.error(request, "Not enough tickets available!")
                    return redirect('event_detail', event_id=event.id)

                total_price = quantity * event.price

                Booking.objects.create(
                    user=request.user,
                    event=event,
                    quantity=quantity,
                    total_price=total_price
                )

                event.available_tickets -= quantity
                event.save()

        except Event.DoesNotExist:
            messages.error(request, "Event not found!")
            return redirect('event_list')

        messages.success(request, "🎉 Ticket booked successfully!")
        return redirect('my_bookings')

    return redirect('event_list')


# 🔹 My Bookings
@login_required(login_url='login')
def my_bookings(request):
    bookings = Booking.objects.filter(
        user=request.user
    ).select_related('event')

    return render(request, "my_bookings.html", {
        "bookings": bookings
    })


# 🔹 Cancel Booking (SAFE RESTORE)
@login_required(login_url='login')
def cancel_booking(request, booking_id):

    try:
        with transaction.atomic():

            booking = get_object_or_404(
                Booking,
                id=booking_id,
                user=request.user
            )

            event = booking.event
            event.available_tickets += booking.quantity
            event.save()

            booking.delete()

    except Exception:
        messages.error(request, "Something went wrong!")
        return redirect('my_bookings')

    messages.success(request, "Booking cancelled successfully!")
    return redirect('my_bookings')


# 🔹 Signup
def signup_page(request):

    if request.method == "POST":

        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists!")
            return redirect("signup")

        User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        messages.success(request, "Account created successfully!")
        return redirect("login")

    return render(request, "signup.html")


# 🔹 Login
def login_page(request):

    if request.method == "POST":

        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(username=username, password=password)

        if user is None:
            messages.error(request, "Invalid username or password")
            return redirect("login")

        login(request, user)
        return redirect("event_list")

    return render(request, "login.html")


# 🔹 Logout
def logout_page(request):
    logout(request)
    return redirect('login')

@login_required(login_url='login')
def dashboard(request):

    total_events = Event.objects.count()
    total_bookings = Booking.objects.count()
    total_users = User.objects.count()

    total_revenue = sum(
        booking.total_price for booking in Booking.objects.all()
    )

    recent_bookings = Booking.objects.select_related('event', 'user').order_by('-id')[:5]

    return render(request, "dashboard.html", {
        "total_events": total_events,
        "total_bookings": total_bookings,
        "total_users": total_users,
        "total_revenue": total_revenue,
        "recent_bookings": recent_bookings
    })