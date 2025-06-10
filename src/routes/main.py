# src/routes/main.py

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from sqlalchemy import func
from src.extensions import db
from src.models.substation import Substation, InspectionTest, ReliabilityMetric
from src.models.user import Role
from src.forms.substation_forms import SubstationForm
import pandas as pd # <--- Ensure this is present

main_bp = Blueprint("main", __name__)

@main_bp.route("/inspections")
@login_required
def inspections():
    # Fetch inspections with related substation and user data *eager loaded*
    inspections = InspectionTest.query.options(db.joinedload(InspectionTest.substation), db.joinedload(InspectionTest.user)).all()
    return render_template("inspections.html", inspections=inspections)

@main_bp.route("/")
@main_bp.route("/dashboard")
@login_required
def dashboard():
    total_substations = Substation.query.count()

    fully_covered = Substation.query.filter_by(coverage_status="Fully Covered").count()
    partially_covered = Substation.query.filter_by(coverage_status="Partially Covered").count()

    inspected_substations = db.session.query(func.count(func.distinct(InspectionTest.substation_id))).filter(InspectionTest.inspection_status == "Inspected").scalar()
    tested_substations = db.session.query(func.count(func.distinct(InspectionTest.substation_id))).filter(InspectionTest.testing_status == "Tested").scalar()

    if total_substations == 0:
        coverage_ratio = 0
        inspection_compliance = 0
        testing_compliance = 0
    else:
        coverage_ratio = (fully_covered + partially_covered * 0.5) / total_substations
        inspection_compliance = inspected_substations / total_substations if total_substations > 0 else 0
        testing_compliance = tested_substations / total_substations if total_substations > 0 else 0

    effective_reliability = (coverage_ratio * 0.4) + \
                            (inspection_compliance * 0.3) + \
                            (testing_compliance * 0.3)

    # Convert to percentage
    effective_reliability *= 100
    coverage_ratio *= 100
    inspection_compliance *= 100
    testing_compliance *= 100

    # Data for charts
    coverage_status_data = db.session.query(Substation.coverage_status, func.count(Substation.id)).group_by(Substation.coverage_status).all()
    coverage_data = {status: count for status, count in coverage_status_data}

    inspection_status_data = db.session.query(InspectionTest.inspection_status, func.count(InspectionTest.id)).group_by(InspectionTest.inspection_status).all()
    inspection_data = {status: count for status, count in inspection_status_data}

    testing_status_data = db.session.query(InspectionTest.testing_status, func.count(InspectionTest.id)).group_by(InspectionTest.testing_status).all()
    testing_data = {status: count for status, count in testing_status_data if status is not None} # Exclude None for testing status

    return render_template("dashboard.html",
                           total_substations=total_substations,
                           effective_reliability=effective_reliability,
                           coverage_ratio=coverage_ratio,
                           inspection_compliance=inspection_compliance,
                           testing_compliance=testing_compliance,
                           coverage_data=coverage_data,
                           inspection_data=inspection_data,
                           testing_data=testing_data)

@main_bp.route("/substations")
@login_required
def substations():
    substations = Substation.query.all()
    return render_template("substations.html", substations=substations)

@main_bp.route("/add_substation", methods=["GET", "POST"])
@login_required
def add_substation():
    form = SubstationForm()
    if form.validate_on_submit():
        new_substation = Substation(
            name=form.name.data,
            coverage_status=form.coverage_status.data
        )
        db.session.add(new_substation)
        db.session.commit()
        flash("Substation added successfully!", "success")
        return redirect(url_for("main.substations"))
    return render_template("add_substation.html", form=form)

@main_bp.route("/edit_substation/<int:id>", methods=["GET", "POST"])
@login_required
def edit_substation(id):
    substation = Substation.query.get_or_404(id)
    form = SubstationForm(obj=substation)
    if form.validate_on_submit():
        substation.name = form.name.data
        substation.coverage_status = form.coverage_status.data
        db.session.commit()
        flash("Substation updated successfully!", "success")
        return redirect(url_for("main.substations"))
    return render_template("edit_substation.html", form=form, substation=substation)

@main_bp.route("/add_inspection", methods=["GET", "POST"])
@login_required
def add_inspection():
    # Only admins and inspectors can add inspection records
    if not current_user.is_inspector():
        flash("You do not have permission to add inspection records.", "danger")
        return redirect(url_for("main.dashboard"))
    
    substations = Substation.query.all()
    # In a real app, you'd use a WTForm for this as well
    if request.method == "POST":
        substation_id = request.form.get("substation_id")
        inspection_date_str = request.form.get("inspection_date")
        testing_date_str = request.form.get("testing_date")
        inspection_status = request.form.get("inspection_status")
        testing_status = request.form.get("testing_status")
        notes = request.form.get("notes")

        try:
            inspection_date = datetime.strptime(inspection_date_str, "%Y-%m-%d").date()
            testing_date = datetime.strptime(testing_date_str, "%Y-%m-%d").date() if testing_date_str else None

            new_inspection = InspectionTest(
                substation_id=substation_id,
                inspection_date=inspection_date,
                testing_date=testing_date,
                inspection_status=inspection_status,
                testing_status=testing_status,
                notes=notes,
                user_id=current_user.id
            )
            db.session.add(new_inspection)
            db.session.commit()
            flash("Inspection record added successfully!", "success")
            return redirect(url_for("main.inspections"))
        except Exception as e:
            db.session.rollback()
            flash(f"Error adding inspection record: {e}", "danger")
    
    return render_template("add_inspection.html", substations=substations)

@main_bp.route("/metrics")
@login_required
def metrics():
    # Weekly Trend
    _weekly_metrics = db.session.query(
        func.to_char(ReliabilityMetric.date, "YYYY-MM-DD").label("date"),
        ReliabilityMetric.reliability_score,
        ReliabilityMetric.testing_compliance,
        ReliabilityMetric.inspection_compliance,
        ReliabilityMetric.coverage_ratio,
        ReliabilityMetric.effective_reliability
    ).filter(ReliabilityMetric.date >= (date.today() - timedelta(weeks=12))).order_by(ReliabilityMetric.date).all()
    
    weekly_metrics = []
    for week_data in _weekly_metrics:
        weekly_metrics.append({
            'date': week_data.date,
            'reliability_score': week_data.reliability_score,
            'testing_compliance': week_data.testing_compliance,
            'inspection_compliance': week_data.inspection_compliance,
            'coverage_ratio': week_data.coverage_ratio,
            'effective_reliability': week_data.effective_reliability
        })

    # Monthly Trend
    _monthly_metrics = db.session.query(
        func.to_char(ReliabilityMetric.date, "YYYY-MM").label("month"),
        func.avg(ReliabilityMetric.reliability_score).label("avg_reliability"),
        func.avg(ReliabilityMetric.testing_compliance).label("avg_testing_compliance"),
        func.avg(ReliabilityMetric.inspection_compliance).label("avg_inspection_compliance"),
        func.avg(ReliabilityMetric.coverage_ratio).label("avg_coverage_ratio"),
        func.avg(ReliabilityMetric.effective_reliability).label("avg_effective_reliability")
    ).filter(ReliabilityMetric.date >= (date.today() - timedelta(days=30*12))).group_by("month").order_by("month").all()
    
    monthly_metrics = []
    for month_data in _monthly_metrics:
        monthly_metrics.append({
            'month': month_data.month,
            'avg_reliability': month_data.avg_reliability,
            'avg_testing_compliance': month_data.avg_testing_compliance,
            'avg_inspection_compliance': month_data.avg_inspection_compliance,
            'avg_coverage_ratio': month_data.avg_coverage_ratio,
            'avg_effective_reliability': month_data.avg_effective_reliability
        })

    # Yearly Trend
    _yearly_metrics = db.session.query(
        func.to_char(ReliabilityMetric.date, "YYYY").label("year"),
        func.avg(ReliabilityMetric.reliability_score).label("avg_reliability"),
        func.avg(ReliabilityMetric.testing_compliance).label("avg_testing_compliance"),
        func.avg(ReliabilityMetric.inspection_compliance).label("avg_inspection_compliance"),
        func.avg(ReliabilityMetric.coverage_ratio).label("avg_coverage_ratio"),
        func.avg(ReliabilityMetric.effective_reliability).label("avg_effective_reliability")
    ).filter(ReliabilityMetric.date >= (date.today() - timedelta(days=365*5))).group_by("year").order_by("year").all()
    
    yearly_metrics = []
    for year_data in _yearly_metrics:
        yearly_metrics.append({
            'year': year_data.year,
            'avg_reliability': year_data.avg_reliability,
            'avg_testing_compliance': year_data.avg_testing_compliance,
            'avg_inspection_compliance': year_data.avg_inspection_compliance,
            'avg_coverage_ratio': year_data.avg_coverage_ratio,
            'avg_effective_reliability': year_data.avg_effective_reliability
        })

    return render_template("metrics.html", 
                           weekly_metrics=weekly_metrics,
                           monthly_metrics=monthly_metrics,
                           yearly_metrics=yearly_metrics)

@main_bp.route("/import_substations", methods=["GET", "POST"])
@login_required
def import_substations():
    # Ensure only admins can access this feature
    if not current_user.is_admin():
        flash("You do not have permission to import substations.", "danger")
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        if "file" not in request.files:
            flash("No file part", "danger")
            return redirect(request.url)
        file = request.files["file"]
        if file.filename == "":
            flash("No selected file", "danger")
            return redirect(request.url)
        
        # Check if the file has an allowed extension
        allowed_extensions = {'xlsx', 'xls', 'csv'}
        if '.' in file.filename and \
           file.filename.rsplit('.', 1)[1].lower() in allowed_extensions:
            try:
                # Read the file based on its extension
                if file.filename.endswith('.csv'):
                    df = pd.read_csv(file)
                else: # Assume .xlsx or .xls
                    df = pd.read_excel(file)

                # Iterate over rows and add substations
                for index, row in df.iterrows():
                    # Ensure column names match your Excel file exactly
                    substation_name = row.get('Substation Name') 
                    coverage_status = row.get('Coverage Status') 

                    if substation_name and coverage_status:
                        # Check if substation already exists
                        existing_substation = Substation.query.filter_by(name=substation_name).first()
                        if not existing_substation:
                            new_substation = Substation(
                                name=substation_name,
                                coverage_status=coverage_status
                            )
                            db.session.add(new_substation)
                        else:
                            flash(f"Substation '{substation_name}' already exists. Skipping import for this entry.", "warning")
                    else:
                        flash(f"Skipping row {index + 2} due to missing 'Substation Name' or 'Coverage Status' in the file.", "warning")
                
                db.session.commit()
                flash("Substations imported successfully!", "success")
                return redirect(url_for("main.substations")) # Redirect to the substations list page
            except Exception as e:
                db.session.rollback()
                flash(f"Error importing substations: {e}", "danger")
        else:
            flash("Invalid file type. Please upload an Excel (.xlsx, .xls) or CSV file.", "danger")

    return render_template("import_substations.html")
