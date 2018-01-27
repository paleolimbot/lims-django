from django.shortcuts import redirect
from django.views import generic
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import authenticate, login, logout
from django import forms
from django.http import HttpResponseForbidden


class LimsLoginMixin(LoginRequiredMixin):
    login_url = reverse_lazy('lims:login')


class LoginForm(forms.Form):
    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput)

    def clean(self):
        super(LoginForm, self).clean()
        user = authenticate(username=self.cleaned_data['username'], password=self.cleaned_data['password'])
        if user is None:
            raise forms.ValidationError('Please enter a valid username and password.')


class LoginView(generic.FormView):
    form_class = LoginForm
    template_name = 'lims/account_login.html'

    def form_valid(self, form):

        redirect_success_url = self.request.GET['next'] if 'next' in self.request.GET else reverse_lazy('lims:index')

        username = form.cleaned_data['username']
        password = form.cleaned_data['password']
        user = authenticate(self.request, username=username, password=password)
        if user is not None:
            login(self.request, user)
            return redirect(redirect_success_url)

        else:
            return HttpResponseForbidden('Login credentials not valid')


class LogoutView(generic.TemplateView):
    template_name = 'lims/account_logout.html'

    def dispatch(self, request, *args, **kwargs):
        # not using LimsLoginMixin because that would redirect the user (confusingly)
        # to the logout page...
        if not request.user.pk:
            return redirect(reverse_lazy('lims:login'))

        logout(request)
        return super(LogoutView, self).dispatch(request, *args, **kwargs)
