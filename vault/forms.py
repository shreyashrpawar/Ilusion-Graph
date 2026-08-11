from django import forms

class UploadFileForm(forms.Form):
    file = forms.FileField(widget=forms.FileInput(attrs={
        'class': 'block w-full text-sm text-slate-300 file:mr-4 file:py-2.5 file:px-4 file:rounded-xl file:border-0 file:text-sm file:font-semibold file:bg-indigo-600 file:text-white hover:file:bg-indigo-500 cursor-pointer bg-slate-950/60 border border-slate-700/60 rounded-xl p-2.5 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 transition-all',
        'id': 'file_input',
        'required': 'required'
    }))
