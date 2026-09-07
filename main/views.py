from django.shortcuts import render, redirect, get_object_or_404
from django.utils.dates import WEEKDAYS_ABBR
from .dates import MONTH_NAMES
from .forms import CommitmentForm
from .models import Commitment
import calendar
import datetime

# Create your views here.
def home(request):
    year = 2026
    firstweekday = 6
    cal = calendar.Calendar(firstweekday=firstweekday)

    weekday_names = [WEEKDAYS_ABBR[(firstweekday + offset) % 7] for offset in range(7)]

    marked_dates = set(
        request.user.commitments.filter(date__year=year).values_list("date", flat=True)
    )

    months = []
    for month_number in range(1, 13):
        weeks = []
        for week in cal.monthdayscalendar(year, month_number):
            cells = []
            for day_number in week:
                if day_number == 0:
                    cells.append(None)
                else:
                    cells.append({
                        "number": day_number,
                        "busy": datetime.date(year, month_number, day_number) in marked_dates,
                    })
            weeks.append(cells)
        months.append({
            "number": month_number,
            "name": MONTH_NAMES[month_number],
            "weeks": weeks,
        })
    return render(request, 'main/home.html', {"year": year, "months": months, "weekday_names": weekday_names})

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


def commitment_edit(request, pk):
    commitment = get_object_or_404(Commitment, pk=pk, user=request.user)

    if request.method == "POST":
        form = CommitmentForm(request.POST, instance=commitment)
        if form.is_valid():
            form.save()
            return redirect(
                "day",
                year=commitment.date.year,
                month=commitment.date.month,
                day=commitment.date.day,
            )
    else:
        form = CommitmentForm(instance=commitment)

    return render(request, "main/commitment_form.html", {
        "form": form,
        "commitment": commitment,
    })

def commitment_delete(request, pk):
    commitment = get_object_or_404(Commitment, pk=pk, user=request.user)

    if request.method == "POST":
        date = commitment.date
        commitment.delete()
        return redirect("day", year=date.year, month=date.month, day=date.day)

    return render(request, "main/commitment_confirm_delete.html", {
        "commitment": commitment,
    })
