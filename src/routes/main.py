# src/routes/main.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from sqlalchemy import func
from sqlalchemy.orm import joinedload # Ensure this import is present if you use it for eager loading

from src.extensions import db
from src.models.substation import Substation, InspectionTest, ReliabilityMetric
from src.models.user import Role
from src.forms.substation_forms import SubstationForm # Ensure this import is present


main_bp = Blueprint("main", __name__)

@main_bp.route("/")
@main_bp.route("/dashboard")
@login_required
def dashboard():
    # Calculate current metrics
    total_substations = Substation.query.count()

    fully_covered = Substation.query.filter_by(coverage_status="Fully Covered").count()
    partially_covered = Substation.query.filter_by(coverage_status="Partially Covered").count()

    inspected_substations = db.session.query(func.count(func.distinct(InspectionTest.substation_id))).filter(InspectionTest.inspection_status == "Inspected").scalar()
    tested_substations = db.session.query(func.count(func.distinct(InspectionTest.substation_id))).filter(InspectionTest.testing_status == "Tested").scalar()

    # Handle division by zero
    if total_substations == 0:
        coverage_ratio = 0
        inspection_compliance = 0
        testing_compliance = 0
    else:
        coverage_ratio = (fully_covered + partially_covered * 0.5) / total_substations
        inspection_compliance = (inspected_substations if inspected_substations is not None else 0) / total_substations
        testing_compliance = (tested_substations if tested_substations is not None else 0) / total_substations

    # Effective Reliability Calculation
    # Assuming full compliance and coverage means 100% reliability
    effective_reliability = (coverage_ratio * inspection_compliance * testing_compliance) * 100

    # Ensure all values are floats for JSON serialization
    coverage_ratio = round(coverage_ratio * 100, 2)
    inspection_compliance = round(inspection_compliance * 100, 2)
    testing_compliance = round(testing_compliance * 100, 2)
    effective_reliability = round(effective_reliability, 2)


    # Chart Data (for dashboard.html)
    coverage_data_raw = db.session.query(Substation.coverage_status, func.count(Substation.id)).group_by(Substation.coverage_status).all()
    coverage_data = {status: count for status, count in coverage_data_raw}

    inspection_data_raw = db.session.query(InspectionTest.inspection_status, func.count(InspectionTest.id)).group_by(InspectionTest.inspection_status).all()
    inspection_data = {status: count for status, count in inspection_data_raw}

    testing_data_raw = db.session.query(InspectionTest.testing_status, func.count(InspectionTest.id)).filter(InspectionTest.testing_status.isnot(None)).group_by(InspectionTest.testing_status).all()
    testing_data = {status: count for status, count in testing_data_raw}


    return render_template("dashboard.html",
                           total_substations=total_substations,
                           effective_reliability=effective_reliability,
                           testing_compliance=testing_compliance,
                           inspection_compliance=inspection_compliance,
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
    if not current_user.is_inspector():
        flash("You do not have permission to add substations.", "danger")
        return redirect(url_for("main.substations"))

    form = SubstationForm()
    if form.validate_on_submit():
        new_substation = Substation(
            name=form.name.data,
            coverage_status=form.coverage_status.data
        )
        try:
            db.session.add(new_substation)
            db.session.commit()
            flash("Substation added successfully!", "success")
            return redirect(url_for("main.substations"))
        except Exception as e:
            db.session.rollback()
            flash(f"Error adding substation: {e}", "danger")
    return render_template("add_substation.html", form=form)


@main_bp.route("/edit_substation/<int:id>", methods=["GET", "POST"])
@login_required
def edit_substation(id):
    if not current_user.is_inspector():
        flash("You do not have permission to edit substations.", "danger")
        return redirect(url_for("main.substations"))

    substation = Substation.query.get_or_404(id)
    form = SubstationForm(obj=substation) # Pre-populate form with existing data

    if form.validate_on_submit():
        substation.name = form.name.data
        substation.coverage_status = form.coverage_status.data
        try:
            db.session.commit()
            flash(f"Substation '{substation.name}' updated successfully!", "success")
            return redirect(url_for("main.substations"))
        except Exception as e:
            db.session.rollback()
            flash(f"Error updating substation: {e}", "danger")

    return render_template("edit_substation.html", form=form, substation=substation)


@main_bp.route("/delete_substation/<int:id>", methods=["POST"])
@login_required
def delete_substation(id):
    if not current_user.is_admin():
        flash("You do not have permission to delete substations.", "danger")
        return redirect(url_for("main.substations"))

    substation = Substation.query.get_or_404(id)

    try:
        # Delete related inspection tests first to maintain integrity if no cascade is set
        InspectionTest.query.filter_by(substation_id=id).delete()
        db.session.delete(substation)
        db.session.commit()
        flash(f"Substation '{substation.name}' and its related inspection records deleted successfully.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting substation: {e}", "danger")

    return redirect(url_for("main.substations"))

@main_bp.route("/inspections")
@login_required
def inspections():
    # Fetch inspections with related substation and user data *eager loaded*
    inspections = InspectionTest.query.options(joinedload(InspectionTest.substation), joinedload(InspectionTest.user)).all()
    return render_template("inspections.html", inspections=inspections)

@main_bp.route("/add_inspection", methods=["GET", "POST"])
@login_required
def add_inspection():
    if not current_user.is_inspector():
        flash("You do not have permission to add inspection records.", "danger")
        return redirect(url_for("main.inspections"))

    substations = Substation.query.all()
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
    # Using func.to_char for PostgreSQL compatibility
    _weekly_metrics = db.session.query(
        func.to_char(ReliabilityMetric.date, "YYYY-IW").label("week"), # Changed to YYYY-IW for ISO week
        func.avg(ReliabilityMetric.reliability_score).label("avg_reliability"),
        func.avg(ReliabilityMetric.testing_compliance).label("avg_testing_compliance"),
        func.avg(ReliabilityMetric.inspection_compliance).label("avg_inspection_compliance"),
        func.avg(ReliabilityMetric.coverage_ratio).label("avg_coverage_ratio"),
        func.avg(ReliabilityMetric.effective_reliability).label("avg_effective_reliability")
    ).filter(ReliabilityMetric.date >= (date.today() - timedelta(weeks=12))).group_by("week").order_by("week").all()

    weekly_metrics = []
    for week_data in _weekly_metrics:
        weekly_metrics.append({
            'date': week_data.week,
            'reliability_score': week_data.avg_reliability,
            'testing_compliance': week_data.avg_testing_compliance,
            'inspection_compliance': week_data.avg_inspection_compliance,
            'coverage_ratio': week_data.avg_coverage_ratio,
            'effective_reliability': week_data.avg_effective_reliability
        })

    # Monthly Trend
    # Using func.to_char for PostgreSQL compatibility
    _monthly_metrics = db.session.query(
        func.to_char(ReliabilityMetric.date, "YYYY-MM").label("month"),
        func.avg(ReliabilityMetric.reliability_score).label("avg_reliability"),
        func.avg(ReliabilityMetric.testing_compliance).label("avg_testing_compliance"),
        func.avg(ReliabilityMetric.inspection_compliance).label("avg_inspection_compliance"),
        func.avg(ReliabilityMetric.coverage_ratio).label("avg_coverage_ratio"),
        func.avg(ReliabilityMetric.effective_reliability).label("avg_effective_reliability")
    ).filter(ReliabilityMetric.date >= (date.today() - timedelta(days=365))).group_by("month").order_by("month").all()

    monthly_metrics = []
    for month_data in _monthly_metrics:
        monthly_metrics.append({
            'date': month_data.month,
            'reliability_score': month_data.avg_reliability,
            'testing_compliance': month_data.avg_testing_compliance,
            'inspection_compliance': month_data.avg_inspection_compliance,
            'coverage_ratio': month_data.avg_coverage_ratio,
            'effective_reliability': month_data.avg_effective_reliability
        })

    # Yearly Trend
    # Using func.to_char for PostgreSQL compatibility
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

