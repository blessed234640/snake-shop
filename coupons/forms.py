from django import forms


class CouponApplyForm(forms.Form):
    code = forms.Charfield()
