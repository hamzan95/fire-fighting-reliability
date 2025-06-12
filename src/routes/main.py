# src/routes/main.py

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from sqlalchemy import func, case, distinct
from sqlalchemy.orm import joinedload  # Import joinedload for eager loading

from src.extensions import db
from src.models.substation import Substation, InspectionTest, ReliabilityMetric
from src.models.user import Role, User  # Ensure User is imported

from src.forms.substation_forms import SubstationForm
from src.forms.inspection_forms import InspectionTestForm  # Keep this import

main_bp = Blueprint("main", __name__)

@main_bp.route("/")
@main_bp.route("/dashboard")
@login_required
def dashboard():
    # Calculate current metrics
    total_substations = Substation.query.count()
    fully_covered = Substation.query.filter_by(coverage_status="Fully Covered").count()
    partially_covered = Substation.query.filter_by(coverage_status="Partially Covered").count()

    # These compliance metrics still count only "Inspected" and "Tested" specifically
    inspected_substations_count = db.session.query(func.count(func.distinct(InspectionTest.substation_id))).filter(InspectionTest.inspection_status == "Inspected").scalar()
    tested_substations_count = db.session.query(func.count(func.distinct(InspectionTest.substation_id))).filter(InspectionTest.testing_status == "Tested").scalar()

    # Handle division by zero for compliance ratios
    if total_substations == 0:
        coverage_ratio = 0
        inspection_compliance = 0
        testing_compliance = 0
    else:
        coverage_ratio = (fully_covered / total_substations) * 100
        inspection_compliance = (inspected_substations_count / total_substations) * 100
        testing_compliance = (tested_substations_count / total_substations) * 100

    # Effective Reliability (assuming a formula, adjust if needed)
    effective_reliability = (inspection_compliance + testing_compliance + coverage_ratio) / 3 if total_substations > 0 else 0

    # Prepare data for Chart.js
    coverage_data = {
        "labels": ["Fully Covered", "Partially Covered", "Not Covered"],
        "data": [fully_covered, partially_covered, total_substations - fully_covered - partially_covered]
    }

    # Inspection Status Distribution (modified for simplified chart view)
    inspection_status_case = case(
        (InspectionTest.inspection_status == "Inspected", "Inspected"),
        else_="Not Inspected"
    ).label("simplified_inspection_status")

    inspection_status_counts = db.session.query(
        inspection_status_case, func.count(InspectionTest.id)
    ).group_by(inspection_status_case).all()
    inspection_data_labels = [label for label, count in inspection_status_counts]
    inspection_data_values = [count for label, count in inspection_status_counts]
    total_inspection_records = db.session.query(func.count(InspectionTest.id)).filter(InspectionTest.inspection_status.isnot(None)).scalar() or 0

    # Testing Status Distribution (modified for simplified chart view)
    testing_status_case = case(
        (InspectionTest.testing_status == "Tested", "Tested"),
        else_="Not Tested"
    ).label("simplified_testing_status")

    testing_status_counts = db.session.query(
        testing_status_case, func.count(InspectionTest.id)
    ).group_by(testing_status_case).all()
    testing_data_labels = [label for label, count in testing_status_counts]
    testing_data_values = [count for label, count in testing_status_counts]
    total_testing_records = db.session.query(func.count(InspectionTest.id)).filter(InspectionTest.testing_status.isnot(None)).scalar() or 0

    # --- FIX: Always provide metrics values to template ---
    latest_metric = ReliabilityMetric.query.order_by(ReliabilityMetric.created_at.desc()).first()
    if latest_metric:
        effective_reliability_metric = latest_metric.effective_reliability
        testing_compliance_metric = latest_metric.testing_compliance
        inspection_compliance_metric = latest_metric.inspection_compliance
    else:
        effective_reliability_metric = 0
        testing_compliance_metric = 0
        inspection_compliance_metric = 0

    return render_template("dashboard.html",
        total_substations=total_substations,
        effective_reliability=effective_reliability_metric,
        testing_compliance=testing_compliance_metric,
        inspection_compliance=inspection_compliance_metric,
        coverage_data=coverage_data,
        inspection_data_labels=inspection_data_labels,
        inspection_data_values=inspection_data_values,
        testing_data_labels=testing_data_labels,
        testing_data_values=testing_data_values,
        total_inspection_records=total_inspection_records,
        total_testing_records=total_testing_records
    )

# ... rest of your main.py code remains unchanged ...

main_bp = Blueprint("main", __name__)

@main_bp.route('/')
@login_required
def dashboard():
    substations = Substation.query.all()
    inspections = InspectionTest.query.all()
    total_substations = len(substations)
    covered_substations = len([s for s in substations if s.coverage_status == 'Covered'])
    coverage_percent = (covered_substations / total_substations) * 100 if total_substations else 0

    total_inspections = len(inspections)
    done_inspections = len([i for i in inspections if i.inspection_status == 'Inspected'])
    inspection_compliance = (done_inspections / total_inspections) * 100 if total_inspections else 0

    reliability_metrics = ReliabilityMetric.query.order_by(ReliabilityMetric.created_at.desc()).first()

    return render_template(
        'dashboard.html',
        coverage_percent=coverage_percent,
        inspection_compliance=inspection_compliance,
        reliability_metrics=reliability_metrics
    )

@main_bp.route('/substations')
@login_required
def substations():
    substations = Substation.query.all()
    return render_template('substations.html', substations=substations)

@main_bp.route('/add_substation', methods=['GET', 'POST'])
@login_required
def add_substation():
    form = SubstationForm()
    if form.validate_on_submit():
        substation = Substation(
            name=form.name.data,
            coverage_status=form.coverage_status.data
        )
        db.session.add(substation)
        db.session.commit()
        flash('Substation added!', 'success')
        return redirect(url_for('main.substations'))
    return render_template('add_substation.html', form=form)

@main_bp.route('/edit_substation/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_substation(id):
    substation = Substation.query.get_or_404(id)
    form = SubstationForm(obj=substation)
    if form.validate_on_submit():
        substation.name = form.name.data
        substation.coverage_status = form.coverage_status.data
        db.session.commit()
        flash('Substation updated!', 'success')
        return redirect(url_for('main.substations'))
    return render_template('edit_substation.html', form=form, substation=substation)

@main_bp.route('/delete_substation/<int:id>', methods=['POST'])
@login_required
def delete_substation(id):
    substation = Substation.query.get_or_404(id)
    db.session.delete(substation)
    db.session.commit()
    flash('Substation deleted!', 'success')
    return redirect(url_for('main.substations'))

@main_bp.route("/inspections")
@login_required
def inspections():
    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)
    query = InspectionTest.query
    if year:
        query = query.filter_by(year=year)
    if month:
        query = query.filter_by(month=month)
    inspections = query.order_by(
        InspectionTest.year.desc(),
        InspectionTest.month.desc(),
        InspectionTest.inspection_date.desc().nullslast(),
        InspectionTest.testing_date.desc().nullslast()
    ).all()

    # Group inspections by year and month for display
    grouped = defaultdict(lambda: defaultdict(list))
    years = set()
    for ins in inspections:
        y = ins.year
        m = ins.month
        grouped[y][m].append(ins)
        years.add(y)

    # Your original logic for tested_substations and not_tested_substations
    tested_substations = []
    not_tested_substations = []
    substations = Substation.query.all()
    for sub in substations:
        latest_inspection = InspectionTest.query.filter_by(substation_id=sub.id)\
            .order_by(InspectionTest.inspection_date.desc().nullslast(), InspectionTest.testing_date.desc().nullslast()).first()
        if latest_inspection:
            sub_dict = {
                "id": sub.id,
                "name": sub.name,
                "latest_inspection_date": latest_inspection.inspection_date or latest_inspection.testing_date,
                "inspection_status": latest_inspection.inspection_status,
                "testing_status": latest_inspection.testing_status,
                "notes": latest_inspection.notes,
                "user_recorded": latest_inspection.user_id
            }
            if latest_inspection.testing_status == "Tested":
                tested_substations.append(sub_dict)
            else:
                not_tested_substations.append(sub_dict)

    return render_template(
        "inspections.html",
        grouped=grouped,
        years=sorted(years, reverse=True),
        selected_year=year,
        selected_month=month,
        tested_substations=tested_substations,
        not_tested_substations=not_tested_substations,
        inspections=inspections
    )

@main_bp.route("/inspections/add", methods=["GET", "POST"])
@login_required
def add_inspection():
    form = InspectionTestForm()
    substations = Substation.query.all()
    form.substation_id.choices = [(s.id, s.name) for s in substations]

    if form.validate_on_submit():
        new_inspection = InspectionTest(
            substation_id=form.substation_id.data,
            inspection_date=form.inspection_date.data,
            testing_date=form.testing_date.data if form.testing_date.data else None,
            inspection_status=form.inspection_status.data,
            testing_status=form.testing_status.data,
            notes=form.notes.data,
            user_id=current_user.id
        )
        new_inspection.set_month_year()
        db.session.add(new_inspection)
        db.session.commit()
        calculate_and_store_monthly_metrics(new_inspection.year, new_inspection.month)
        calculate_and_store_yearly_metrics(new_inspection.year)
        flash("Inspection record added successfully!", "success")
        return redirect(url_for("main.inspections"))
    return render_template("add_inspection.html", form=form, substations=substations)

@main_bp.route("/inspections/edit/<int:inspection_id>", methods=["GET", "POST"])
@login_required
def edit_inspection(inspection_id):
    inspection = InspectionTest.query.get_or_404(inspection_id)
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
        inspection.set_month_year()
        db.session.commit()
        calculate_and_store_monthly_metrics(inspection.year, inspection.month)
        calculate_and_store_yearly_metrics(inspection.year)
        flash("Inspection record updated successfully!", "success")
        return redirect(url_for("main.inspections"))
    return render_template("edit_inspection.html", form=form, inspection_id=inspection.id, substations=substations)

def calculate_and_store_monthly_metrics(year, month):
    total = InspectionTest.query.filter_by(year=year, month=month).count()
    inspected = InspectionTest.query.filter_by(year=year, month=month, inspection_status='Inspected').count()
    tested = InspectionTest.query.filter_by(year=year, month=month, testing_status='Tested').count()
    substations_count = Substation.query.count()
    inspection_compliance = (inspected / substations_count) * 100 if substations_count else 0
    testing_compliance = (tested / substations_count) * 100 if substations_count else 0
    effective_reliability = (inspection_compliance + testing_compliance) / 2 if substations_count else 0

    ReliabilityMetric.query.filter_by(year=year, month=month).delete()
    metric = ReliabilityMetric(
        year=year,
        month=month,
        effective_reliability=effective_reliability,
        testing_compliance=testing_compliance,
        inspection_compliance=inspection_compliance
    )
    db.session.add(metric)
    db.session.commit()

def calculate_and_store_yearly_metrics(year):
    total = InspectionTest.query.filter_by(year=year).count()
    inspected = InspectionTest.query.filter_by(year=year, inspection_status='Inspected').count()
    tested = InspectionTest.query.filter_by(year=year, testing_status='Tested').count()
    substations_count = Substation.query.count()
    inspection_compliance = (inspected / substations_count) * 100 if substations_count else 0
    testing_compliance = (tested / substations_count) * 100 if substations_count else 0
    effective_reliability = (inspection_compliance + testing_compliance) / 2 if substations_count else 0

    ReliabilityMetric.query.filter_by(year=year, month=None).delete()
    metric = ReliabilityMetric(
        year=year,
        month=None,
        effective_reliability=effective_reliability,
        testing_compliance=testing_compliance,
        inspection_compliance=inspection_compliance
    )
    db.session.add(metric)
    db.session.commit()

@main_bp.route('/metrics')
@login_required
def metrics():
    metrics = ReliabilityMetric.query.order_by(ReliabilityMetric.created_at.desc()).all()
    return render_template('metrics.html', metrics=metrics)

@main_bp.route('/add_metric', methods=['GET', 'POST'])
@login_required
def add_metric():
    if request.method == 'POST':
        year = int(request.form['year'])
        month = int(request.form['month'])
        effective_reliability = float(request.form['effective_reliability'])
        testing_compliance = float(request.form['testing_compliance'])
        inspection_compliance = float(request.form['inspection_compliance'])
        metric = ReliabilityMetric(
            year=year,
            month=month,
            effective_reliability=effective_reliability,
            testing_compliance=testing_compliance,
            inspection_compliance=inspection_compliance
        )
        db.session.add(metric)
        db.session.commit()
        flash('Metric added!', 'success')
        return redirect(url_for('main.metrics'))
    return render_template('add_metric.html')

@main_bp.route('/delete_metric/<int:id>', methods=['POST'])
@login_required
def delete_metric(id):
    metric = ReliabilityMetric.query.get_or_404(id)
    db.session.delete(metric)
    db.session.commit()
    flash('Metric deleted!', 'success')
    return redirect(url_for('main.metrics'))

@main_bp.route('/import_substations', methods=['GET', 'POST'])
@login_required
def import_substations():
    if request.method == 'POST':
        file = request.files['file']
        if not file:
            flash('No file selected.', 'danger')
            return redirect(request.url)
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        csv_input = csv.reader(stream)
        for row in csv_input:
            if len(row) < 2:
                continue
            name, coverage_status = row[0], row[1]
            if not Substation.query.filter_by(name=name).first():
                substation = Substation(name=name, coverage_status=coverage_status)
                db.session.add(substation)
        db.session.commit()
        flash('Substations imported!', 'success')
        return redirect(url_for('main.substations'))
    return render_template('import_substations.html')

@main_bp.route('/export_substations')
@login_required
def export_substations():
    substations = Substation.query.all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Name', 'Coverage Status'])
    for s in substations:
        writer.writerow([s.name, s.coverage_status])
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype='text/csv',
        as_attachment=True,
        download_name='substations.csv'
    )

