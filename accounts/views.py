from django.urls import reverse_lazy
from django.views.generic import CreateView

from .forms import CustomUserCreationForm
from django.contrib.auth.decorators import login_not_required
from django.utils.decorators import method_decorator
# Create your views here.

@method_decorator(login_not_required, name='dispatch')
class RegisterView(CreateView):
    form_class = CustomUserCreationForm
    template_name = 'accounts/register.html'
    success_url = reverse_lazy('accounts:login')