"""Resources app forms."""

from django import forms

from .models import Category, Resource, Subject


class ResourceUploadForm(forms.ModelForm):
    """Form for uploading a new resource."""

    class Meta:
        model = Resource
        fields = ("title", "description", "category", "visibility", "subjects")
        widgets = {
            "title": forms.TextInput(
                attrs={"class": "form-control", "maxlength": "200"}
            ),
            "description": forms.Textarea(
                attrs={"class": "form-control", "rows": 4, "maxlength": "2000"}
            ),
            "category": forms.Select(attrs={"class": "form-select"}),
            "visibility": forms.Select(attrs={"class": "form-select"}),
            "subjects": forms.SelectMultiple(attrs={"class": "form-select"}),
        }
        labels = {
            "title": "Title",
            "description": "Description",
            "category": "Category",
            "visibility": "Visibility",
            "subjects": "Subjects",
        }
        help_texts = {
            "subjects": "Hold Ctrl (or Cmd) to select multiple subjects.",
        }

    subjects = forms.ModelMultipleChoiceField(
        queryset=Subject.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={"class": "form-select"}),
    )

    file = forms.FileField(required=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = Category.objects.all()
        self.fields["category"].empty_label = "Select a category"
        self.fields["category"].required = True

    def clean_title(self):
        title = self.cleaned_data.get("title", "").strip()
        if len(title) < 1:
            raise forms.ValidationError("Title is required.")
        if len(title) > 200:
            raise forms.ValidationError("Title is too long.")
        return title

    def clean_description(self):
        description = self.cleaned_data.get("description") or ""
        if len(description) > 2000:
            raise forms.ValidationError("Description is too long.")
        return description.strip()


class ResourceEditForm(forms.ModelForm):
    """Form for editing resource metadata (no file replacement)."""

    class Meta:
        model = Resource
        fields = ("title", "description", "category", "visibility", "subjects")
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "visibility": forms.Select(attrs={"class": "form-select"}),
            "subjects": forms.SelectMultiple(attrs={"class": "form-select"}),
        }

    subjects = forms.ModelMultipleChoiceField(
        queryset=Subject.objects.all(), required=False,
        widget=forms.SelectMultiple(attrs={"class": "form-select"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = Category.objects.all()
        self.fields["category"].empty_label = "Select a category"
