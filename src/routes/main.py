from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from src.models.substation import db, Substation, InspectionTest, ReliabilityMetric
from datetime import datetime, date
import json

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Home page with dashboard overview"""
    return render_template('index.html')

@main_bp.route('/substations')
def substations():
    """List all substations"""
    substations = Substation.query.all()
    return render_template('substations.html', substations=substations)

@main_bp.route('/substations/add', methods=['GET', 'POST'])
def add_substation():
    """Add a new substation"""
    if request.method == 'POST':
        substation_id = request.form.get('substation_id')
        substation_name = request.form.get('substation_name')
        coverage_status = request.form.get('coverage_status')
        
        # Check if substation already exists
        existing = Substation.query.filter_by(substation_id=substation_id).first()
        if existing:
            flash('Substation ID already exists', 'error')
            return redirect(url_for('main.add_substation'))
        
        new_substation = Substation(
            substation_id=substation_id,
            substation_name=substation_name,
            coverage_status=coverage_status
        )
        
        db.session.add(new_substation)
        db.session.commit()
        
        flash('Substation added successfully', 'success')
        return redirect(url_for('main.substations'))
    
    return render_template('add_substation.html')

@main_bp.route('/substations/edit/<substation_id>', methods=['GET', 'POST'])
def edit_substation(substation_id):
    """Edit an existing substation"""
    substation = Substation.query.filter_by(substation_id=substation_id).first_or_404()
    
    if request.method == 'POST':
        substation.substation_name = request.form.get('substation_name')
        substation.coverage_status = request.form.get('coverage_status')
        
        db.session.commit()
        
        flash('Substation updated successfully', 'success')
        return redirect(url_for('main.substations'))
    
    return render_template('edit_substation.html', substation=substation)

@main_bp.route('/inspections')
def inspections():
    """List all inspections"""
    inspections = InspectionTest.query.order_by(InspectionTest.inspection_date.desc()).all()
    return render_template('inspections.html', inspections=inspections)

@main_bp.route('/inspections/add', methods=['GET', 'POST'])
def add_inspection():
    """Add a new inspection record"""
    substations = Substation.query.all()
    
    if request.method == 'POST':
        substation_id = request.form.get('substation_id')
        inspection_status = request.form.get('inspection_status')
        testing_status = request.form.get('testing_status')
        inspection_date = datetime.strptime(request.form.get('inspection_date'), '%Y-%m-%d').date()
        notes = request.form.get('notes')
        
        new_inspection = InspectionTest(
            substation_id=substation_id,
            inspection_status=inspection_status,
            testing_status=testing_status,
            inspection_date=inspection_date,
            notes=notes
        )
        
        db.session.add(new_inspection)
        db.session.commit()
        
        # Recalculate metrics for this date
        calculate_metrics(inspection_date)
        
        flash('Inspection record added successfully', 'success')
        return redirect(url_for('main.inspections'))
    
    return render_template('add_inspection.html', substations=substations, today=date.today())

@main_bp.route('/metrics')
def metrics():
    """View reliability metrics"""
    metrics = ReliabilityMetric.query.order_by(ReliabilityMetric.calculation_date.desc()).all()
    return render_template('metrics.html', metrics=metrics)

@main_bp.route('/api/metrics/latest')
def latest_metrics():
    """API endpoint to get latest metrics for dashboard"""
    metric = ReliabilityMetric.query.order_by(ReliabilityMetric.calculation_date.desc()).first()
    
    if not metric:
        return jsonify({
            'success': False,
            'message': 'No metrics available'
        })
    
    return jsonify({
        'success': True,
        'data': {
            'date': metric.calculation_date.strftime('%Y-%m-%d'),
            'testing_compliance': metric.testing_compliance,
            'inspection_compliance': metric.inspection_compliance,
            'coverage_ratio': metric.coverage_ratio,
            'effective_reliability': metric.effective_reliability,
            'total_substations': metric.total_substations,
            'fully_covered': metric.fully_covered_substations,
            'partially_covered': metric.partially_covered_substations,
            'not_covered': metric.not_covered_substations,
            'inspected': metric.inspected_substations,
            'not_inspected': metric.not_inspected_substations,
            'tested': metric.tested_substations,
            'not_tested': metric.not_tested_substations
        }
    })

@main_bp.route('/api/metrics/trend/<period>')
def metrics_trend(period):
    """API endpoint to get trend data for charts"""
    if period == 'weekly':
        # Get last 12 weeks of data
        metrics = ReliabilityMetric.query.order_by(ReliabilityMetric.calculation_date.desc()).limit(12).all()
    elif period == 'monthly':
        # Get last 12 months of data (simplified for demo)
        metrics = ReliabilityMetric.query.order_by(ReliabilityMetric.calculation_date.desc()).limit(12).all()
    elif period == 'yearly':
        # Get last 5 years of data (simplified for demo)
        metrics = ReliabilityMetric.query.order_by(ReliabilityMetric.calculation_date.desc()).limit(5).all()
    else:
        return jsonify({'success': False, 'message': 'Invalid period'})
    
    # Reverse to get chronological order
    metrics.reverse()
    
    dates = [m.calculation_date.strftime('%Y-%m-%d') for m in metrics]
    testing_compliance = [m.testing_compliance for m in metrics]
    inspection_compliance = [m.inspection_compliance for m in metrics]
    coverage_ratio = [m.coverage_ratio for m in metrics]
    effective_reliability = [m.effective_reliability for m in metrics]
    
    return jsonify({
        'success': True,
        'data': {
            'dates': dates,
            'testing_compliance': testing_compliance,
            'inspection_compliance': inspection_compliance,
            'coverage_ratio': coverage_ratio,
            'effective_reliability': effective_reliability
        }
    })

@main_bp.route('/dashboard')
def dashboard():
    """Main dashboard view"""
    return render_template('dashboard.html')

def calculate_metrics(calculation_date):
    """Calculate reliability metrics for a given date"""
    # Get all substations
    substations = Substation.query.all()
    total_substations = len(substations)
    
    if total_substations == 0:
        return
    
    # Count coverage status
    fully_covered = sum(1 for s in substations if s.coverage_status == 'Fully Covered')
    partially_covered = sum(1 for s in substations if s.coverage_status == 'Partially Covered')
    not_covered = sum(1 for s in substations if s.coverage_status == 'Not Covered')
    
    # Get latest inspection for each substation up to the calculation date
    inspected = 0
    not_inspected = 0
    tested = 0
    not_tested = 0
    
    for substation in substations:
        # Get the latest inspection record for this substation up to the calculation date
        latest_inspection = InspectionTest.query.filter(
            InspectionTest.substation_id == substation.substation_id,
            InspectionTest.inspection_date <= calculation_date
        ).order_by(InspectionTest.inspection_date.desc()).first()
        
        if latest_inspection:
            if latest_inspection.inspection_status == 'Inspected':
                inspected += 1
            else:
                not_inspected += 1
                
            if latest_inspection.testing_status == 'Tested':
                tested += 1
            else:
                not_tested += 1
        else:
            # No inspection record found, count as not inspected and not tested
            not_inspected += 1
            not_tested += 1
    
    # Calculate metrics
    testing_compliance = (tested / total_substations) * 100 if total_substations > 0 else 0
    inspection_compliance = (inspected / total_substations) * 100 if total_substations > 0 else 0
    
    coverage_numerator = fully_covered + (partially_covered * 0.5)
    coverage_ratio = (coverage_numerator / total_substations) * 100 if total_substations > 0 else 0
    
    # Calculate effective reliability
    testing_ratio = tested / total_substations if total_substations > 0 else 0
    inspection_ratio = inspected / total_substations if total_substations > 0 else 0
    coverage_ratio_decimal = coverage_numerator / total_substations if total_substations > 0 else 0
    effective_reliability = coverage_ratio_decimal * inspection_ratio * testing_ratio * 100
    
    # Check if metrics for this date already exist
    existing_metric = ReliabilityMetric.query.filter_by(calculation_date=calculation_date).first()
    
    if existing_metric:
        # Update existing metric
        existing_metric.total_substations = total_substations
        existing_metric.fully_covered_substations = fully_covered
        existing_metric.partially_covered_substations = partially_covered
        existing_metric.not_covered_substations = not_covered
        existing_metric.inspected_substations = inspected
        existing_metric.not_inspected_substations = not_inspected
        existing_metric.tested_substations = tested
        existing_metric.not_tested_substations = not_tested
        existing_metric.testing_compliance = testing_compliance
        existing_metric.inspection_compliance = inspection_compliance
        existing_metric.coverage_ratio = coverage_ratio
        existing_metric.effective_reliability = effective_reliability
    else:
        # Create new metric
        new_metric = ReliabilityMetric(
            calculation_date=calculation_date,
            total_substations=total_substations,
            fully_covered_substations=fully_covered,
            partially_covered_substations=partially_covered,
            not_covered_substations=not_covered,
            inspected_substations=inspected,
            not_inspected_substations=not_inspected,
            tested_substations=tested,
            not_tested_substations=not_tested,
            testing_compliance=testing_compliance,
            inspection_compliance=inspection_compliance,
            coverage_ratio=coverage_ratio,
            effective_reliability=effective_reliability
        )
        db.session.add(new_metric)
    
    db.session.commit()
