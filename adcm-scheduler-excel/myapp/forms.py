from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django import forms
from django.forms import ModelForm, Textarea
from django.urls import reverse_lazy


class FileFieldForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(*args, **kwargs)
        self.helper.form_action = reverse_lazy("upload_gantt")

        self.helper.add_input(Submit("submit", "Отправить"))

    file_field = forms.FileField(widget=forms.ClearableFileInput(attrs={"multiple": True}))


class UploadFileForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(*args, **kwargs)
        self.helper.form_action = reverse_lazy("upload")

        self.helper.add_input(Submit("submit", "Отправить"))

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
    weight = forms.FloatField(label="Weight", required=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_action = "add_link"
        self.helper.form_class = "form-inline"
        self.helper.add_input(Submit("submit", "Отправить"))


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
        self.helper.form_action = "add_node"
        self.helper.form_class = "form-inline"
        self.helper.add_input(Submit("submit", "Отправить"))
