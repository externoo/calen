from django.shortcuts import render, redirect
from .forms import CommitmentForm
import calendar
import datetime

# Create your views here.
def home(request):
    year = 2026
    cal = calendar.Calendar(firstweekday=6)  

    months = []
    for month_number in range(1, 13):
        months.append({
            "number": month_number,
            "name": calendar.month_name[month_number],
            "weeks": cal.monthdayscalendar(year, month_number),
        })
    return render(request, 'main/home.html', {"year": year, "months": months})

def day(request, year, month, day):
    date = datetime.date(year, month, day)

    if request.method == "POST":
        form = CommitmentForm(request.POST)
        if form.is_valid():
            commitment = form.save(commit=False)
            commitment.user = request.user
            commitment.date = date
            commitment.save()
            return redirect("day", year=year, month=month, day=day)
    else:
        form = CommitmentForm()

    commitments = request.user.commitments.filter(date=date)
    return render(request, "main/day.html",{
        "date": date, 
        "commitments": commitments,
        "form": form,
    })
