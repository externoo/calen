from django import forms
from .models import Commitment

class CommitmentForm(forms.ModelForm):
    class Meta:
        model = Commitment
        fields = ("text",)
