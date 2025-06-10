from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField
from wtforms.validators import DataRequired, Length
from flask_wtf import FlaskForm
from wtforms import SubmitField

class DeleteSubstationForm(FlaskForm):
    submit = SubmitField('Delete')
class SubstationForm(FlaskForm):
    name = StringField(
        "Substation Name",
        validators=[DataRequired(), Length(min=2, max=100)],
        render_kw={"class": "form-control"} # Bootstrap styling
    )
    coverage_status = SelectField(
        "Coverage Status",
        choices=[
            ("", "Select Status"), # Placeholder
            ("Fully Covered", "Fully Covered"),
            ("Partially Covered", "Partially Covered"),
            ("Not Covered", "Not Covered")
        ],
        validators=[DataRequired(message="Please select a coverage status.")],
        render_kw={"class": "form-select"} # Bootstrap styling
    )
    submit = SubmitField(
        "Submit",
        render_kw={"class": "btn btn-primary"} # Bootstrap styling
    )
