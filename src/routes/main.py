# src/routes/main.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from sqlalchemy import func

from src.extensions import db
from src.models.substation import Substation, InspectionTest, ReliabilityMetric
from src.models.user import Role
from src.forms.substation_forms import SubstationForm


main_bp = Blueprint("main", __name__)

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
        inspection_compliance = inspected_substations / total_substations
        testing_compliance = tested_substations / total_substations

    # Effective Reliability Calculation (example, adjust as needed)
    effective_reliability = (coverage_ratio + inspection_compliance + testing_compliance) / 3 * 100

    # Store daily metric (only if there's data)
    if total_substations > 0:
        today = date.today()
        metric = ReliabilityMetric.query.filter_by(date=today).first()
        if not metric:
            metric = ReliabilityMetric(
                date=today,
                reliability_score=effective_reliability,
                testing_compliance=testing_compliance * 100,
                inspection_compliance=inspection_compliance * 100,
                coverage_ratio=coverage_ratio * 100,
                effective_reliability=effective_reliability
            )
            db.session.add(metric)
        else:
            metric.reliability_score = effective_reliability
            metric.testing_compliance = testing_compliance * 100
            metric.inspection_compliance = inspection_compliance * 100
            metric.coverage_ratio = coverage_ratio * 100
            metric.effective_reliability = effective_reliability
        db.session.commit()

    # Data for charts
    coverage_data = {
        "Fully Covered": fully_covered,
        "Partially Covered": partially_covered,
        "Not Covered": total_substations - fully_covered - partially_covered
    }

    inspection_data = {
        "Inspected": inspected_substations,
        "Not Inspected": total_substations - inspected_substations
    }

    tested_count = db.session.query(func.count(func.distinct(InspectionTest.substation_id))).filter(InspectionTest.testing_status == "Tested").scalar()
    not_tested_count = total_substations - tested_count

    testing_data = {
        "Tested": tested_count,
        "Not Tested": not_tested_count
    }

    return render_template("dashboard.html",
                           total_substations=total_substations,
                           effective_reliability=effective_reliability,
                           testing_compliance=testing_compliance * 100, # Display as percentage
                           inspection_compliance=inspection_compliance * 100, # Display as percentage
                           coverage_ratio=coverage_ratio * 100,
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
    # Serialize substations to a list of dictionaries to pass to the template
    substations_data = []
    for sub in substations:
        substations_data.append({
            'id': sub.id,
            'name': sub.name,
            'coverage_status': sub.coverage_status
        })
    return render_template("substations.html", substations=substations_data)

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


@main_bp.route("/edit_substation/<int:id>", methods=["GET", "POST"])
@login_required
def edit_substation(id):
    if not current_user.is_admin():
        flash("You do not have permission to edit substations.", "danger")
        return redirect(url_for("main.substations"))

    substation = Substation.query.get_or_404(id)
    form = SubstationForm(obj=substation) # Pre-fill form with existing data

    if form.validate_on_submit():
        substation.name = form.name.data
        substation.coverage_status = form.coverage_status.data
        db.session.commit()
        flash(f"Substation '{substation.name}' updated successfully!", "success")
        return redirect(url_for("main.substations"))
    
    return render_template("edit_substation.html", title="Edit Substation", form=form, substation=substation)


@main_bp.route("/delete_substation/<int:id>", methods=["POST"])
@login_required
def delete_substation(id):
    if not current_user.is_admin():
        flash("You do not have permission to delete substations.", "danger")
        return redirect(url_for("main.substations"))

    substation = Substation.query.get_or_404(id)
    try:
        # Delete related inspection records first to avoid foreign key constraints
        InspectionTest.query.filter_by(substation_id=substation.id).delete()
        db.session.delete(substation)
        db.session.commit()
        flash(f"Substation '{substation.name}' and its inspection records deleted successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting substation: {e}", "danger")
    
    return redirect(url_for("main.substations"))


@main_bp.route("/inspections")
@login_required
def inspections():
    if not current_user.is_inspector():
        flash("You do not have permission to view inspections.", "danger")
        return redirect(url_for("main.dashboard"))
    inspections = InspectionTest.query.order_by(InspectionTest.created_at.desc()).all()
    # Serialize inspections to a list of dictionaries to pass to the template
    inspections_data = []
    for inspection in inspections:
        inspections_data.append({
            'substation_name': inspection.substation.name, # Access substation name
            'inspection_date': inspection.inspection_date.strftime("%Y-%m-%d"),
            'testing_date': inspection.testing_date.strftime("%Y-%m-%d") if inspection.testing_date else "N/A",
            'inspection_status': inspection.inspection_status,
            'testing_status': inspection.testing_status if inspection.testing_status else "N/A",
            'notes': inspection.notes,
            'recorded_by': inspection.user.username if inspection.user else "N/A",
            'created_at': inspection.created_at.strftime("%Y-%m-%d %H:%M")
        })
    return render_template("inspections.html", inspections=inspections_data)


@main_bp.route("/add_inspection", methods=["GET", "POST"])
@login_required
def add_inspection():
    if not current_user.is_inspector() and not current_user.is_admin():
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
    if not current_user.is_admin():
        flash("You do not have permission to view metrics.", "danger")
        return redirect(url_for("main.dashboard"))
    
    # Weekly Trend
    # Using func.to_char for PostgreSQL compatibility
    weekly_metrics_raw = db.session.query(
        func.to_char(ReliabilityMetric.date, "YYYY-WW").label("week"), # Changed to_char format for week
        func.avg(ReliabilityMetric.reliability_score).label("avg_reliability"),
        func.avg(ReliabilityMetric.testing_compliance).label("avg_testing_compliance"),
        func.avg(ReliabilityMetric.inspection_compliance).label("avg_inspection_compliance"),
        func.avg(ReliabilityMetric.coverage_ratio).label("avg_coverage_ratio"),
        func.avg(ReliabilityMetric.effective_reliability).label("avg_effective_reliability")
    ).filter(ReliabilityMetric.date >= (date.today() - timedelta(weeks=12))).group_by("week").order_by("week").all()

    weekly_metrics = []
    for week_data in weekly_metrics_raw:
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
    monthly_metrics_raw = db.session.query(
        func.to_char(ReliabilityMetric.date, "YYYY-MM").label("month"),
        func.avg(ReliabilityMetric.reliability_score).label("avg_reliability"),
        func.avg(ReliabilityMetric.testing_compliance).label("avg_testing_compliance"),
        func.avg(ReliabilityMetric.inspection_compliance).label("avg_inspection_compliance"),
        func.avg(ReliabilityMetric.coverage_ratio).label("avg_coverage_ratio"),
        func.avg(ReliabilityMetric.effective_reliability).label("avg_effective_reliability")
    ).filter(ReliabilityMetric.date >= (date.today() - timedelta(days=365))).group_by("month").order_by("month").all()

    monthly_metrics = []
    for month_data in monthly_metrics_raw:
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
