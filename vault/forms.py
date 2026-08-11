from django import forms
from django.core.exceptions import ValidationError

MAX_FILE_SIZE_BYTES = 200 * 1024 * 1024  # 200 MB

class UploadFileForm(forms.Form):
    file = forms.FileField(widget=forms.FileInput(attrs={
        'class': 'block w-full text-sm text-slate-300 file:mr-4 file:py-2.5 file:px-4 file:rounded-xl file:border-0 file:text-sm file:font-semibold file:bg-indigo-600 file:text-white hover:file:bg-indigo-500 cursor-pointer bg-slate-950/60 border border-slate-700/60 rounded-xl p-2.5 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 transition-all',
        'id': 'file_input',
        'required': 'required'
    }))

    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file and file.size > MAX_FILE_SIZE_BYTES:
            raise ValidationError("Maximum file size is 200 mb.")
        return file
