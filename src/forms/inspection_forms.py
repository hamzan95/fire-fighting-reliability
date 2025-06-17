from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, DateField, SelectField, TextAreaField
from wtforms.validators import DataRequired, Optional
from wtforms_sqlalchemy.fields import QuerySelectField
from src.models.substation import Substation # Assuming Substation model is correctly imported

class InspectionTestForm(FlaskForm):
    substation_id = SelectField(
        "Substation",
        coerce=int,
        validators=[DataRequired()],
        render_kw={"class": "form-select js-example-basic-single"}
    )
    inspection_date = DateField(
        "Inspection Date",
        validators=[DataRequired()],
        format='%Y-%m-%d', # Ensure date format matches HTML input type="date"
        render_kw={"class": "form-control"}
    )
    testing_date = DateField(
        "Testing Date (Optional)",
        validators=[Optional()],
        format='%Y-%m-%d',
        render_kw={"class": "form-control"}
    )
    inspection_status = SelectField(
        "Inspection Status",
        choices=[
            ("Inspected", "Inspected"),
            ("Pending", "Pending"),
            ("Failed", "Failed")
        ],
        validators=[DataRequired()],
        render_kw={"class": "form-select"}
    )
    testing_status = SelectField(
        "Testing Status",
        choices=[
            ("Tested", "Tested"),
            ("Pending", "Pending"),
            ("Failed", "Failed"),
            ("N/A", "N/A")
        ],
        validators=[DataRequired()],
        render_kw={"class": "form-select"}
    )
    notes = TextAreaField(
        "Notes",
        render_kw={"class": "form-control", "rows": 3}
    )
    submit = SubmitField(
        "Submit",
        render_kw={"class": "btn btn-primary"}
    )

    # Optional: A query factory if you were using QuerySelectField directly, but we use SelectField with choices populated in route
    # def get_substations():
    #     return Substation.query.all()
    # substation = QuerySelectField(query_factory=get_substations, get_label='name', allow_blank=False, validators=[DataRequired()])
