from django import forms
from django.forms import ModelForm, Textarea
from django.urls import reverse_lazy
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from myapp.models import Rule, Wbs


class SdrForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)

    class Meta:
        model = Wbs
        fields = ['wbs_code', 'docsdiv', 'wbs1', 'wbs2', 'wbs3', 'specs']


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


class AddLink(forms.Form):
    from_din = forms.CharField(
        label="From DIN",
        max_length=80,
        required=True,
    )
    to_din = forms.CharField(
        label="To DIN",
        max_length=80,
        required=True,
    )
    weight = forms.FloatField(
        label="Weight",
        required=True
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_action = 'add_link'
        self.helper.form_class = 'form-inline'
        self.helper.add_input(Submit('submit', 'Отправить'))


class AddNode(forms.Form):
    din = forms.CharField(
        label="DIN",
        max_length=80,
        required=True,
    )
    name = forms.CharField(
        label="Name",
        max_length=80,
        required=True,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_action = 'add_node'
        self.helper.form_class = 'form-inline'
        self.helper.add_input(Submit('submit', 'Отправить'))
