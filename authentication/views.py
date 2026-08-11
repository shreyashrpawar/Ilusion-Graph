import uuid
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import render, redirect

from application.graph.graph import execute_query
from authentication.forms import UserRegistrationForm


@login_required(login_url='login')
def homepage(request):
    return render(request, 'homepage.html')


def register(request):
    form = UserRegistrationForm()

    if request.method == "POST":
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = True
            user.save()

            query = """
            CREATE (u:User {
                id: $id,
                username: $username,
                email: $email
            })
            RETURN u
            """
            try:
                execute_query(
                    query,
                    id=int(uuid.uuid4().int & 0x7fffffff),
                    username=user.username,
                    email=user.email or ""
                )
            except Exception as e:
                print(f"Neo4j node creation notice: {e}")

            return redirect('login')
        else:
            messages.error(request, 'Account creation failed. Please try again.')

    return render(request, 'authentication/register.html', {
        'form': form
    })
