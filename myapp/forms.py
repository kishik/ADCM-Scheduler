from django import forms
from django.forms import ModelForm
from models import Work


class WorkForm(ModelForm):
    class Meta:
        model = Work
        fields = ['id', 'name']


class URNForm(forms.Form):
    id = forms.IntegerField()
    type = forms.CharField()
    urn = forms.CharField()

