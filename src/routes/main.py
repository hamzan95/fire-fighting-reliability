# src/routes/main.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from sqlalchemy import func
from sqlalchemy.orm import joinedload # Import joinedload for eager loading

from src.extensions import db
from src.models.substation import Substation, InspectionTest, ReliabilityMetric
from src.models.user import Role
from src.forms.substation_forms import SubstationForm # Assuming this is used for add/edit substation
from src.forms.inspection_forms import InspectionTestForm # ADD THIS LINE

main_bp = Blueprint("main", __name__)

@main_bp.route("/")
@main_bp.route("/dashboard")
@login_required
def dashboard():
    # Calculate current metrics
    total_substations = Substation.query.count()
    
    fully_covered = Substation.query.filter_by(coverage_status="Fully Covered").count()
    partially_covered = Substation.query.filter_by(coverage_status="Partially Covered").count()
    not_covered = Substation.query.filter_by(coverage_status="Not Covered").count() # Ensure 'Not Covered' is also counted for completeness

    # Calculate inspected and not inspected substations
    # Get count of distinct substations that have at least one 'Inspected' inspection
    inspected_count = db.session.query(func.count(func.distinct(InspectionTest.substation_id))).filter(InspectionTest.inspection_status == "Inspected").scalar()
    if inspected_count is None: # Handle case where no inspections exist
        inspected_count = 0

    # Calculate not inspected substations
    not_inspected_count = total_substations - inspected_count

    # Calculate tested substations
    tested_substations = db.session.query(func.count(func.distinct(InspectionTest.substation_id))).filter(InspectionTest.testing_status == "Tested").scalar()
    if tested_substations is None: # Handle case where no testing records exist
        tested_substations = 0
    
    # Handle division by zero
    if total_substations == 0:
        coverage_ratio = 0
        inspection_compliance = 0
        testing_compliance = 0
    else:
        coverage_ratio = (fully_covered / total_substations) * 100
        inspection_compliance = (inspected_count / total_substations) * 100 # Use inspected_count here
        testing_compliance = (tested_substations / total_substations) * 100

    # Prepare data for charts
    coverage_data = {
        "Fully Covered": fully_covered,
        "Partially Covered": partially_covered,
        "Not Covered": not_covered
    }

    inspection_data = {
        "labels": ["Inspected", "Not Inspected"],
        "datasets": [{
            "data": [inspected_count, not_inspected_count],
            "backgroundColor": ["#28a745", "#dc3545"] # Green for Inspected, Red for Not Inspected
        }]
    }

    testing_data = {
        "Tested": tested_substations,
        "Pending": db.session.query(func.count(func.distinct(InspectionTest.substation_id))).filter(InspectionTest.testing_status == "Pending").scalar() or 0,
        "Failed": db.session.query(func.count(func.distinct(InspectionTest.substation_id))).filter(InspectionTest.testing_status == "Failed").scalar() or 0,
        "N/A": db.session.query(func.count(func.distinct(InspectionTest.substation_id))).filter(InspectionTest.testing_status == "N/A").scalar() or 0
    }

    # Fetch recent inspections for the table
    recent_inspections = InspectionTest.query.options(joinedload(InspectionTest.substation))\
                                            .order_by(InspectionTest.inspection_date.desc()).limit(10).all()

    # Fetch total users for dashboard display
    from src.models.user import User # Local import to avoid circular dependency if User imports db.session or anything that causes issues
    total_users = User.query.count()

    return render_template("dashboard.html",
                           total_substations=total_substations,
                           effective_reliability=75.0, # Placeholder, replace with actual calculation if available
                           testing_compliance=testing_compliance,
                           inspection_compliance=inspection_compliance,
                           coverage_data=coverage_data,
                           inspection_data=inspection_data,
                           testing_data=testing_data,
                           recent_inspections=recent_inspections,
                           total_users=total_users
                           )


@main_bp.route("/substations")
@login_required
def substations():
    if not current_user.is_inspector() and not current_user.is_admin():
        flash("You do not have permission to view substations.", "danger")
        return redirect(url_for("main.dashboard"))
    
    substations = Substation.query.all()
    # Pass a form instance for adding/editing a substation if needed on the same page
    from src.forms.substation_forms import SubstationForm # Import here to avoid circular imports if forms also depend on models/db
    form = SubstationForm()
    
    # Fetch latest inspection status for each substation
    substations_with_status = []
    for sub in substations:
        latest_inspection = InspectionTest.query.filter_by(substation_id=sub.id)\
                                .order_by(InspectionTest.inspection_date.desc()).first()
        sub_status = {
            "id": sub.id,
            "name": sub.name,
            "coverage_status": sub.coverage_status,
            "last_inspection_date": latest_inspection.inspection_date.strftime('%Y-%m-%d') if latest_inspection else 'N/A',
            "inspection_status": latest_inspection.inspection_status if latest_inspection else 'Not Inspected', # Default if no inspection
            "testing_status": latest_inspection.testing_status if latest_inspection else 'N/A', # Default if no inspection
            "created_at": sub.created_at.strftime('%Y-%m-%d %H:%M:%S')
        }
        substations_with_status.append(sub_status)


    return render_template("substations.html", substations=substations_with_status, form=form)

@main_bp.route("/substations/add", methods=["GET", "POST"])
@login_required
def add_substation():
    if not current_user.is_admin():
        flash("You do not have permission to add substations.", "danger")
        return redirect(url_for("main.dashboard"))
    
    from src.forms.substation_forms import SubstationForm
    form = SubstationForm()
    if form.validate_on_submit():
        new_substation = Substation(name=form.name.data, coverage_status=form.coverage_status.data)
        db.session.add(new_substation)
        try:
            db.session.commit()
            flash("Substation added successfully!", "success")
            return redirect(url_for("main.substations"))
        except Exception as e:
            db.session.rollback()
            flash(f"Error adding substation: {e}", "danger")
    return render_template("add_substation.html", form=form) # Assuming a dedicated add_substation.html

@main_bp.route("/substations/edit/<int:substation_id>", methods=["GET", "POST"])
@login_required
def edit_substation(substation_id):
    if not current_user.is_admin():
        flash("You do not have permission to edit substations.", "danger")
        return redirect(url_for("main.dashboard"))
    
    substation = Substation.query.get_or_404(substation_id)
    from src.forms.substation_forms import SubstationForm
    form = SubstationForm(obj=substation) # Populate form with existing data

    if form.validate_on_submit():
        substation.name = form.name.data
        substation.coverage_status = form.coverage_status.data
        try:
            db.session.commit()
            flash("Substation updated successfully!", "success")
            return redirect(url_for("main.substations"))
        except Exception as e:
            db.session.rollback()
            flash(f"Error updating substation: {e}", "danger")
    
    return render_template("edit_substation.html", form=form, substation_id=substation.id) # Assuming edit_substation.html

@main_bp.route("/substations/delete/<int:substation_id>", methods=["POST"])
@login_required
def delete_substation(substation_id):
    if not current_user.is_admin():
        flash("You do not have permission to delete substations.", "danger")
        return redirect(url_for("main.dashboard"))

    substation = Substation.query.get_or_404(substation_id)
    try:
        db.session.delete(substation)
        db.session.commit()
        flash("Substation deleted successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting substation: {e}", "danger")
    return redirect(url_for("main.substations"))

@main_bp.route("/inspections")
@login_required
def inspections():
    if not current_user.is_inspector() and not current_user.is_admin():
        flash("You do not have permission to view inspections.", "danger")
        return redirect(url_for("main.dashboard"))
    
    inspections = InspectionTest.query.options(joinedload(InspectionTest.substation)).order_by(InspectionTest.inspection_date.desc()).all()
    return render_template("inspections.html", inspections=inspections) # Assuming an inspections.html

@main_bp.route("/inspections/add", methods=["GET", "POST"])
@login_required
def add_inspection():
    if not current_user.is_inspector() and not current_user.is_admin():
        flash("You do not have permission to add inspections.", "danger")
        return redirect(url_for("main.dashboard"))
    
    from src.forms.inspection_forms import InspectionTestForm # THIS IMPORT IS NOW AT THE TOP
    form = InspectionTestForm()
    substations = Substation.query.all() # Fetch all substations for the dropdown
    form.substation_id.choices = [(s.id, s.name) for s in substations] # Populate choices

    if form.validate_on_submit():
        new_inspection = InspectionTest(
            substation_id=form.substation_id.data,
            inspection_date=form.inspection_date.data,
            testing_date=form.testing_date.data if form.testing_date.data else None,
            inspection_status=form.inspection_status.data,
            testing_status=form.testing_status.data,
            notes=form.notes.data,
            user_id=current_user.id # Assign the current user as the inspector
        )
        db.session.add(new_inspection)
        try:
            db.session.commit()
            flash("Inspection record added successfully!", "success")
            return redirect(url_for("main.inspections"))
        except Exception as e:
            db.session.rollback()
            flash(f"Error adding inspection: {e}", "danger")
    return render_template("add_inspection.html", form=form, substations=substations) # Pass substations for the dropdown

@main_bp.route("/inspections/edit/<int:inspection_id>", methods=["GET", "POST"])
@login_required
def edit_inspection(inspection_id):
    if not current_user.is_inspector() and not current_user.is_admin():
        flash("You do not have permission to edit inspections.", "danger")
        return redirect(url_for("main.dashboard"))

    inspection = InspectionTest.query.get_or_404(inspection_id)
    from src.forms.inspection_forms import InspectionTestForm # THIS IMPORT IS NOW AT THE TOP
    form = InspectionTestForm(obj=inspection)
    substations = Substation.query.all()
    form.substation_id.choices = [(s.id, s.name) for s in substations]

    if form.validate_on_submit():
        inspection.substation_id = form.substation_id.data
        inspection.inspection_date = form.inspection_date.data
        inspection.testing_date = form.testing_date.data if form.testing_date.data else None
        inspection.inspection_status = form.inspection_status.data
        inspection.testing_status = form.testing_status.data
        inspection.notes = form.notes.data
        # user_id is set at creation, usually not changed on edit unless specific requirement
        try:
            db.session.commit()
            flash("Inspection record updated successfully!", "success")
            return redirect(url_for("main.inspections"))
        except Exception as e:
            db.session.rollback()
            flash(f"Error updating inspection: {e}", "danger")
    
    return render_template("edit_inspection.html", form=form, inspection_id=inspection.id, substations=substations)

@main_bp.route("/inspections/delete/<int:inspection_id>", methods=["POST"])
@login_required
def delete_inspection(inspection_id):
    if not current_user.is_admin():
        flash("You do not have permission to delete inspections.", "danger")
        return redirect(url_for("main.dashboard"))

    inspection = InspectionTest.query.get_or_404(inspection_id)
    try:
        db.session.delete(inspection)
        db.session.commit()
        flash("Inspection record deleted successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting inspection: {e}", "danger")
    return redirect(url_for("main.inspections"))


@main_bp.route("/metrics")
@login_required
def metrics():
    # Placeholder for metrics calculation logic
    # This would involve querying historical ReliabilityMetric data
    
    # Example: fetch last 12 weekly metrics
    weekly_metrics = ReliabilityMetric.query.filter(ReliabilityMetric.interval_type == 'weekly')\
                                            .order_by(ReliabilityMetric.calculated_at.desc()).limit(12).all()
    weekly_metrics = sorted(weekly_metrics, key=lambda x: x.calculated_at) # Sort by date for chart

    monthly_metrics = ReliabilityMetric.query.filter(ReliabilityMetric.interval_type == 'monthly')\
                                            .order_by(ReliabilityMetric.calculated_at.desc()).limit(12).all()
    monthly_metrics = sorted(monthly_metrics, key=lambda x: x.calculated_at)

    yearly_metrics = ReliabilityMetric.query.filter(ReliabilityMetric.interval_type == 'yearly')\
                                            .order_by(ReliabilityMetric.calculated_at.desc()).limit(5).all()
    yearly_metrics = sorted(yearly_metrics, key=lambda x: x.calculated_at)

    return render_template("metrics.html", 
                           weekly_metrics=weekly_metrics,
                           monthly_metrics=monthly_metrics,
                           yearly_metrics=yearly_metrics)

@main_bp.route("/substations/bulk_edit", methods=["POST"])
@login_required
def bulk_edit_substations():
    if not current_user.is_admin():
        flash("You do not have permission to perform bulk edits on substations.", "danger")
        return redirect(url_for("main.substations"))

    selected_ids_str = request.form.get("selected_substation_ids")
    new_coverage_status = request.form.get("new_coverage_status")

    if not selected_ids_str:
        flash("No substations selected for bulk edit.", "warning")
        return redirect(url_for("main.substations"))
    
    if not new_coverage_status:
        flash("No new coverage status selected.", "warning")
        return redirect(url_for("main.substations"))

    try:
        substation_ids = [int(s_id) for s_id in selected_ids_str.split(',') if s_id.strip()]
        
        # Perform the bulk update
        # Using synchronize_session='fetch' or False can affect how SQLAlchemy handles existing objects in session
        # 'evaluate' (default) might not work well with .in_() for updates
        # 'fetch' reloads affected objects, 'False' assumes objects are not in session or handles them manually
        num_updated = db.session.query(Substation).filter(Substation.id.in_(substation_ids)).update(
            {"coverage_status": new_coverage_status},
            synchronize_session='fetch'
        )
        db.session.commit()
        flash(f"Successfully updated coverage status for {num_updated} substations to '{new_coverage_status}'.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error during bulk edit: {e}", "danger")
    
    return redirect(url_for("main.substations"))
