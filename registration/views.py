from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import redirect, render


def register(response):
    if response.method == "POST":
        form = UserCreationForm(response.POST)

        if form.is_valid():
            form.save()
        return redirect("/")
    else:
        form = UserCreationForm()

    return render(response, "registration/registration.html", {"form": form})
