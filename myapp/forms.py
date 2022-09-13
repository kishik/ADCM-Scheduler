from django import forms
from django.forms import ModelForm, Textarea
from django.urls import reverse_lazy
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from myapp.models import Rule, Wbs


class URNForm(forms.Form):
    id = forms.IntegerField()
    type = forms.CharField()
    urn = forms.CharField()


class RuleForm(ModelForm):
    class Meta:
        model = Rule
        fields = ['name', 'rule']
        widgets = {
            'rule': Textarea(attrs={'cols': 150, 'rows': 30}),
        }


class WbsForm(ModelForm):
    class Meta:
        model = Wbs
        fields = ['wbs_code', 'docsdiv', 'wbs1', 'wbs2', 'wbs3', 'specs']


class UploadFileForm(forms.Form):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(*args, **kwargs)
        self.helper.form_action = reverse_lazy("upload")
        self.helper.add_input(Submit('submit', 'Отправить'))

    file = forms.FileField()
