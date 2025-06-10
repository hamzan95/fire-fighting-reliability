from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from sqlalchemy import func
from src.models.substation import db, Substation, InspectionTest, ReliabilityMetric
from src.models.user import Role
from src.forms.substation_forms import SubstationForm # <--- ADD THIS IMPORT
from src.forms.auth_forms import RegistrationForm # Keep this if you register users from main.py

main_bp = Blueprint("main", __name__)

@main_bp.route("/")
@main_bp.route("/dashboard")
@login_required
def dashboard():
    # ... (Your existing dashboard logic remains the same) ...
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
        inspection_compliance = inspected_substations / total_substations
        testing_compliance = tested_substations / total_substations

    effective_reliability = (coverage_ratio + inspection_compliance + testing_compliance) / 3 * 100 if total_substations > 0 else 0

    # Data for charts (assuming these are dicts from your current logic)
    coverage_data = {
        "Fully Covered": fully_covered,
        "Partially Covered": partially_covered,
        "Not Covered": total_substations - fully_covered - partially_covered
    }
    inspection_data = {
        "Inspected": inspected_substations,
        "Not Inspected": total_substations - inspected_substations # Assuming all other substations are 'Not Inspected' for simplicity
    }
    testing_data = {
        "Tested": tested_substations,
        "Not Tested": total_substations - tested_substations # Assuming all other substations are 'Not Tested' for simplicity
    }

    return render_template("dashboard.html",
                           total_substations=total_substations,
                           effective_reliability=effective_reliability,
                           testing_compliance=testing_compliance * 100, # Display as percentage
                           inspection_compliance=inspection_compliance * 100, # Display as percentage
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
    if not current_user.is_admin():
        flash("You do not have permission to add substations.", "danger")
        return redirect(url_for("main.substations"))

    form = SubstationForm() # <--- Use the new form
    if form.validate_on_submit():
        substation = Substation(
            name=form.name.data,
            coverage_status=form.coverage_status.data
        )
        db.session.add(substation)
        db.session.commit()
        flash("Substation added successfully!", "success")
        return redirect(url_for("main.substations"))
    
    return render_template("add_substation.html", title="Add Substation", form=form) # Pass the form to the template

# --- START NEW ROUTES FOR EDIT/DELETE SUBSTATION ---

@main_bp.route("/edit_substation/<int:id>", methods=["GET", "POST"])
@login_required
def edit_substation(id):
    if not current_user.is_admin():
        flash("You do not have permission to edit substations.", "danger")
        return redirect(url_for("main.substations"))

    substation = Substation.query.get_or_404(id)
    form = SubstationForm()

    if form.validate_on_submit():
        substation.name = form.name.data
        substation.coverage_status = form.coverage_status.data
        db.session.commit()
        flash(f"Substation '{substation.name}' updated successfully!", "success")
        return redirect(url_for("main.substations"))
    elif request.method == "GET":
        # Pre-fill form fields with existing substation data
        form.name.data = substation.name
        form.coverage_status.data = substation.coverage_status
    
    return render_template("edit_substation.html", title="Edit Substation", form=form, substation=substation)


@main_bp.route("/delete_substation/<int:id>", methods=["POST"])
@login_required
def delete_substation(id):
    if not current_user.is_admin():
        flash("You do not have permission to delete substations.", "danger")
        return redirect(url_for("main.substations"))

    substation = Substation.query.get_or_404(id)
    try:
        db.session.delete(substation)
        db.session.commit()
        flash(f"Substation '{substation.name}' deleted successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting substation: {e}", "danger")
    
    return redirect(url_for("main.substations"))

# --- END NEW ROUTES ---

# ... (rest of your main.py routes like metrics, add_inspection, etc. remain here) ...

@main_bp.route("/metrics")
@login_required
def metrics():
    # Weekly Trend (last 12 weeks)
    weekly_metrics = db.session.query(
        func.strftime("%W", ReliabilityMetric.date).label("week"),
        func.avg(ReliabilityMetric.reliability_score).label("avg_reliability"),
        func.avg(ReliabilityMetric.testing_compliance).label("avg_testing_compliance"),
        func.avg(ReliabilityMetric.inspection_compliance).label("avg_inspection_compliance"),
        func.avg(ReliabilityMetric.coverage_ratio).label("avg_coverage_ratio"),
        func.avg(ReliabilityMetric.effective_reliability).label("avg_effective_reliability")
    ).filter(ReliabilityMetric.date >= (date.today() - timedelta(weeks=12))).group_by("week").order_by("week").all()
    
    # Convert weekly metrics to a list of dictionaries for easier JavaScript consumption
    _weekly_metrics = []
    for week_data in weekly_metrics:
        _weekly_metrics.append({
            'date': f"Week {week_data.week}", # Adjust label for Chart.js
            'reliability_score': week_data.avg_reliability,
            'testing_compliance': week_data.avg_testing_compliance,
            'inspection_compliance': week_data.avg_inspection_compliance,
            'coverage_ratio': week_data.avg_coverage_ratio,
            'effective_reliability': week_data.avg_effective_reliability
        })

    # Monthly Trend (last 12 months)
    monthly_metrics = db.session.query(
        func.strftime("%Y-%m", ReliabilityMetric.date).label("month"),
        func.avg(ReliabilityMetric.reliability_score).label("avg_reliability"),
        func.avg(ReliabilityMetric.testing_compliance).label("avg_testing_compliance"),
        func.avg(ReliabilityMetric.inspection_compliance).label("avg_inspection_compliance"),
        func.avg(ReliabilityMetric.coverage_ratio).label("avg_coverage_ratio"),
        func.avg(ReliabilityMetric.effective_reliability).label("avg_effective_reliability")
    ).filter(ReliabilityMetric.date >= (date.today() - timedelta(days=365))).group_by("month").order_by("month").all()

    _monthly_metrics = []
    for month_data in monthly_metrics:
        _monthly_metrics.append({
            'month': month_data.month,
            'avg_reliability': month_data.avg_reliability,
            'avg_testing_compliance': month_data.avg_testing_compliance,
            'avg_inspection_compliance': month_data.avg_inspection_compliance,
            'avg_coverage_ratio': month_data.avg_coverage_ratio,
            'avg_effective_reliability': month_data.avg_effective_reliability
        })

    # Yearly Trend (last 5 years)
    yearly_metrics = db.session.query(
        func.strftime("%Y", ReliabilityMetric.date).label("year"),
        func.avg(ReliabilityMetric.reliability_score).label("avg_reliability"),
        func.avg(ReliabilityMetric.testing_compliance).label("avg_testing_compliance"),
        func.avg(ReliabilityMetric.inspection_compliance).label("avg_inspection_compliance"),
        func.avg(ReliabilityMetric.coverage_ratio).label("avg_coverage_ratio"),
        func.avg(ReliabilityMetric.effective_reliability).label("avg_effective_reliability")
    ).filter(ReliabilityMetric.date >= (date.today() - timedelta(days=365*5))).group_by("year").order_by("year").all()
    
    _yearly_metrics = []
    for year_data in yearly_metrics:
        _yearly_metrics.append({
            'year': year_data.year,
            'avg_reliability': year_data.avg_reliability,
            'avg_testing_compliance': year_data.avg_testing_compliance,
            'avg_inspection_compliance': year_data.avg_inspection_compliance,
            'avg_coverage_ratio': year_data.avg_coverage_ratio,
            'avg_effective_reliability': year_data.avg_effective_reliability
        })

    return render_template("metrics.html",
                           weekly_metrics=_weekly_metrics,
                           monthly_metrics=_monthly_metrics,
                           yearly_metrics=_yearly_metrics)

@main_bp.route("/inspections")
@login_required
def inspections():
    inspections = InspectionTest.query.order_by(InspectionTest.created_at.desc()).all()
    return render_template("inspections.html", inspections=inspections)


@main_bp.route("/add_inspection", methods=["GET", "POST"])
@login_required
def add_inspection():
    if not current_user.is_inspector() and not current_user.is_admin():
        flash("You do not have permission to add inspection records.", "danger")
        return redirect(url_for("main.inspections"))
    
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
