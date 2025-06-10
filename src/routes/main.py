
# src/routes/main.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from sqlalchemy import func
from sqlalchemy.orm import joinedload # Import joinedload for eager loading

from src.extensions import db
from src.models.substation import Substation, InspectionTest, ReliabilityMetric
from src.models.user import Role
from src.forms.substation_forms import SubstationForm


main_bp = Blueprint("main", __name__)

@main_bp.route("/inspections")
@login_required
def inspections():
    # Fetch inspections with related substation and user data *eager loaded*
    inspections = InspectionTest.query.options(joinedload(InspectionTest.substation), joinedload(InspectionTest.user)).all()
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
        inspection_compliance = (inspected_substations / total_substations) * 100
        testing_compliance = (tested_substations / total_substations) * 100

    # Reliability Score (example calculation)
    # This is a simplified example, you might have a more complex formula
    reliability_score = (coverage_ratio * 0.4 + (inspection_compliance / 100) * 0.3 + (testing_compliance / 100) * 0.3) * 100
    
    # Effective Reliability
    # This metric considers both coverage and operational compliance
    effective_reliability = reliability_score * (coverage_ratio) # Example formula


    # Store daily metrics
    today = date.today()
    metric = ReliabilityMetric.query.filter_by(date=today).first()
    if not metric:
        metric = ReliabilityMetric(
            date=today,
            reliability_score=reliability_score,
            testing_compliance=testing_compliance,
            inspection_compliance=inspection_compliance,
            coverage_ratio=coverage_ratio * 100, # Store as percentage
            effective_reliability=effective_reliability
        )
        db.session.add(metric)
    else:
        metric.reliability_score = reliability_score
        metric.testing_compliance = testing_compliance
        metric.inspection_compliance = inspection_compliance
        metric.coverage_ratio = coverage_ratio * 100
        metric.effective_reliability = effective_reliability
    db.session.commit()

    # Get data for charts
    coverage_data = {
        "Fully Covered": fully_covered,
        "Partially Covered": partially_covered,
        "Not Covered": total_substations - fully_covered - partially_covered
    }

    inspection_data = {
        "Inspected": inspected_substations,
        "Not Inspected": total_substations - inspected_substations
    }

    testing_data = {
        "Tested": tested_substations,
        "Not Tested": total_substations - tested_substations
    }

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
    if not current_user.is_inspector():
        flash("You do not have permission to view substations.", "danger")
        return redirect(url_for("main.dashboard"))
    
    substations = Substation.query.all()
    return render_template("substations.html", substations=substations)

@main_bp.route("/add_substation", methods=["GET", "POST"])
@login_required
def add_substation():
    if not current_user.is_inspector():
        flash("You do not have permission to add substations.", "danger")
        return redirect(url_for("main.dashboard"))
    
    form = SubstationForm()
    if form.validate_on_submit():
        new_substation = Substation(name=form.name.data, coverage_status=form.coverage_status.data)
        db.session.add(new_substation)
        db.session.commit()
        flash("Substation added successfully!", "success")
        return redirect(url_for("main.substations"))
    
    return render_template("add_substation.html", form=form)

@main_bp.route("/edit_substation/<int:id>", methods=["GET", "POST"])
@login_required
def edit_substation(id):
    if not current_user.is_inspector():
        flash("You do not have permission to edit substations.", "danger")
        return redirect(url_for("main.dashboard"))
    
    substation = Substation.query.get_or_404(id)
    form = SubstationForm(obj=substation)
    if form.validate_on_submit():
        substation.name = form.name.data
        substation.coverage_status = form.coverage_status.data
        db.session.commit()
        flash("Substation updated successfully!", "success")
        return redirect(url_for("main.substations"))
    
    return render_template("edit_substation.html", form=form, substation=substation)

@main_bp.route("/delete_substation/<int:id>", methods=["POST"])
@login_required
def delete_substation(id):
    if not current_user.is_admin():
        flash("You do not have permission to delete substations.", "danger")
        return redirect(url_for("main.substations"))

    substation = Substation.query.get_or_404(id)
    try:
        # Delete related inspection records first
        InspectionTest.query.filter_by(substation_id=substation.id).delete()
        db.session.delete(substation)
        db.session.commit()
        flash("Substation and its related inspection records deleted successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting substation: {e}", "danger")
    return redirect(url_for("main.substations"))


@main_bp.route("/add_inspection", methods=["GET", "POST"])
@login_required
def add_inspection():
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
    if not current_user.is_admin() and not current_user.is_inspector():
        flash("You do not have permission to view metrics.", "danger")
        return redirect(url_for("main.dashboard"))

    # Weekly Trend
    # Using func.strftime for SQLite compatibility; for PostgreSQL, use func.to_char(ReliabilityMetric.date, 'YYYY-MM-DD')
    # and adjust the grouping.
    # For weekly, we can group by week of the year and year.
    _weekly_metrics = db.session.query(
        func.strftime("%Y-%W", ReliabilityMetric.date).label("week"), # %W for week number (00-53)
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
    # Using func.strftime for SQLite compatibility; for PostgreSQL, use func.to_char(ReliabilityMetric.date, 'YYYY-MM')
    _monthly_metrics = db.session.query(
        func.strftime("%Y-%m", ReliabilityMetric.date).label("month"),
        func.avg(ReliabilityMetric.reliability_score).label("avg_reliability"),
        func.avg(ReliabilityMetric.testing_compliance).label("avg_testing_compliance"),
        func.avg(ReliabilityMetric.inspection_compliance).label("avg_inspection_compliance"),
        func.avg(ReliabilityMetric.coverage_ratio).label("avg_coverage_ratio"),
        func.avg(ReliabilityMetric.effective_reliability).label("avg_effective_reliability")
    ).filter(ReliabilityMetric.date >= (date.today() - timedelta(days=365))).group_by("month").order_by("month").all()

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
    # Using func.to_char for PostgreSQL compatibility
    yearly_metrics_raw = db.session.query(
        func.to_char(ReliabilityMetric.date, "YYYY").label("year"),
        func.avg(ReliabilityMetric.reliability_score).label("avg_reliability"),
        func.avg(ReliabilityMetric.testing_compliance).label("avg_testing_compliance"),
        func.avg(ReliabilityMetric.inspection_compliance).label("avg_inspection_compliance"),
        func.avg(ReliabilityMetric.coverage_ratio).label("avg_coverage_ratio"),
        func.avg(ReliabilityMetric.effective_reliability).label("avg_effective_reliability")
    ).filter(ReliabilityMetric.date >= (date.today() - timedelta(days=365*5))).group_by("year").order_by("year").all()
    
    yearly_metrics = []
    for year_data in yearly_metrics_raw:
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
