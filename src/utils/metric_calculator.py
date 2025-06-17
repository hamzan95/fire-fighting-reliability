# src/utils/metric_calculator.py
from datetime import datetime, date, timedelta
from calendar import monthrange
from sqlalchemy import func, extract
from src.extensions import db
from src.models.substation import Substation, InspectionTest, ReliabilityMetric

class MetricCalculator:
    
    @staticmethod
    def calculate_current_metrics():
        """Calculate current reliability metrics"""
        total_substations = Substation.query.count()
        
        if total_substations == 0:
            return {
                'total_substations': 0,
                'coverage_ratio': 0,
                'inspection_compliance': 0,
                'testing_compliance': 0,
                'effective_reliability': 0
            }
        
        fully_covered = Substation.query.filter_by(coverage_status="Fully Covered").count()
        partially_covered = Substation.query.filter_by(coverage_status="Partially Covered").count()
        
        inspected_substations_count = db.session.query(func.count(func.distinct(InspectionTest.substation_id))).filter(InspectionTest.inspection_status == "Inspected").scalar()
        tested_substations_count = db.session.query(func.count(func.distinct(InspectionTest.substation_id))).filter(InspectionTest.testing_status == "Tested").scalar()
        
        coverage_ratio = (fully_covered + partially_covered * 0.5) / total_substations * 100
        inspection_compliance = inspected_substations_count / total_substations * 100
        testing_compliance = tested_substations_count / total_substations * 100
        
        # Original formula: (coverage + inspection + testing) / 3
        effective_reliability = (coverage_ratio + inspection_compliance + testing_compliance) / 3
        
        return {
            'total_substations': total_substations,
            'coverage_ratio': coverage_ratio,
            'inspection_compliance': inspection_compliance,
            'testing_compliance': testing_compliance,
            'effective_reliability': effective_reliability
        }
    
    @staticmethod
    def store_daily_metric():
        """Store today's reliability metric"""
        metrics = MetricCalculator.calculate_current_metrics()
        
        if metrics['total_substations'] > 0:
            today = date.today()
            
            # Check if today's metric already exists
            existing_metric = ReliabilityMetric.query.filter_by(
                date=today, 
                period_type='daily'
            ).first()
            
            if existing_metric:
                # Update existing metric
                existing_metric.reliability_score = metrics['effective_reliability']
                existing_metric.testing_compliance = metrics['testing_compliance']
                existing_metric.inspection_compliance = metrics['inspection_compliance']
                existing_metric.coverage_ratio = metrics['coverage_ratio']
                existing_metric.effective_reliability = metrics['effective_reliability']
            else:
                # Create new metric
                new_metric = ReliabilityMetric(
                    date=today,
                    period_type='daily',
                    reliability_score=metrics['effective_reliability'],
                    testing_compliance=metrics['testing_compliance'],
                    inspection_compliance=metrics['inspection_compliance'],
                    coverage_ratio=metrics['coverage_ratio'],
                    effective_reliability=metrics['effective_reliability']
                )
                db.session.add(new_metric)
            
            db.session.commit()
            return True
        return False
    
    @staticmethod
    def calculate_monthly_metrics(year, month):
        """Calculate monthly aggregated metrics for a specific month"""
        # Get the first and last day of the month
        first_day = date(year, month, 1)
        last_day = date(year, month, monthrange(year, month)[1])
        
        # Query daily metrics for this month
        daily_metrics = ReliabilityMetric.query.filter(
            ReliabilityMetric.date >= first_day,
            ReliabilityMetric.date <= last_day,
            ReliabilityMetric.period_type == 'daily'
        ).all()
        
        if not daily_metrics:
            return None
        
        # Calculate averages
        avg_reliability = sum(m.reliability_score for m in daily_metrics) / len(daily_metrics)
        avg_testing_compliance = sum(m.testing_compliance for m in daily_metrics) / len(daily_metrics)
        avg_inspection_compliance = sum(m.inspection_compliance for m in daily_metrics) / len(daily_metrics)
        avg_coverage_ratio = sum(m.coverage_ratio for m in daily_metrics) / len(daily_metrics)
        avg_effective_reliability = sum(m.effective_reliability for m in daily_metrics) / len(daily_metrics)
        
        return {
            'date': first_day,  # Use first day of month as the date
            'reliability_score': avg_reliability,
            'testing_compliance': avg_testing_compliance,
            'inspection_compliance': avg_inspection_compliance,
            'coverage_ratio': avg_coverage_ratio,
            'effective_reliability': avg_effective_reliability
        }
    
    @staticmethod
    def store_monthly_metric(year, month):
        """Store monthly aggregated metric"""
        monthly_data = MetricCalculator.calculate_monthly_metrics(year, month)
        
        if monthly_data:
            # Check if monthly metric already exists
            existing_metric = ReliabilityMetric.query.filter_by(
                date=monthly_data['date'],
                period_type='monthly'
            ).first()
            
            if existing_metric:
                # Update existing metric
                existing_metric.reliability_score = monthly_data['reliability_score']
                existing_metric.testing_compliance = monthly_data['testing_compliance']
                existing_metric.inspection_compliance = monthly_data['inspection_compliance']
                existing_metric.coverage_ratio = monthly_data['coverage_ratio']
                existing_metric.effective_reliability = monthly_data['effective_reliability']
            else:
                # Create new metric
                new_metric = ReliabilityMetric(
                    date=monthly_data['date'],
                    period_type='monthly',
                    reliability_score=monthly_data['reliability_score'],
                    testing_compliance=monthly_data['testing_compliance'],
                    inspection_compliance=monthly_data['inspection_compliance'],
                    coverage_ratio=monthly_data['coverage_ratio'],
                    effective_reliability=monthly_data['effective_reliability']
                )
                db.session.add(new_metric)
            
            db.session.commit()
            return True
        return False
    
    @staticmethod
    def calculate_yearly_metrics(year):
        """Calculate yearly aggregated metrics for a specific year"""
        # Get the first and last day of the year
        first_day = date(year, 1, 1)
        last_day = date(year, 12, 31)
        
        # Query monthly metrics for this year
        monthly_metrics = ReliabilityMetric.query.filter(
            ReliabilityMetric.date >= first_day,
            ReliabilityMetric.date <= last_day,
            ReliabilityMetric.period_type == 'monthly'
        ).all()
        
        if not monthly_metrics:
            return None
        
        # Calculate averages
        avg_reliability = sum(m.reliability_score for m in monthly_metrics) / len(monthly_metrics)
        avg_testing_compliance = sum(m.testing_compliance for m in monthly_metrics) / len(monthly_metrics)
        avg_inspection_compliance = sum(m.inspection_compliance for m in monthly_metrics) / len(monthly_metrics)
        avg_coverage_ratio = sum(m.coverage_ratio for m in monthly_metrics) / len(monthly_metrics)
        avg_effective_reliability = sum(m.effective_reliability for m in monthly_metrics) / len(monthly_metrics)
        
        return {
            'date': first_day,  # Use first day of year as the date
            'reliability_score': avg_reliability,
            'testing_compliance': avg_testing_compliance,
            'inspection_compliance': avg_inspection_compliance,
            'coverage_ratio': avg_coverage_ratio,
            'effective_reliability': avg_effective_reliability
        }
    
    @staticmethod
    def store_yearly_metric(year):
        """Store yearly aggregated metric"""
        yearly_data = MetricCalculator.calculate_yearly_metrics(year)
        
        if yearly_data:
            # Check if yearly metric already exists
            existing_metric = ReliabilityMetric.query.filter_by(
                date=yearly_data['date'],
                period_type='yearly'
            ).first()
            
            if existing_metric:
                # Update existing metric
                existing_metric.reliability_score = yearly_data['reliability_score']
                existing_metric.testing_compliance = yearly_data['testing_compliance']
                existing_metric.inspection_compliance = yearly_data['inspection_compliance']
                existing_metric.coverage_ratio = yearly_data['coverage_ratio']
                existing_metric.effective_reliability = yearly_data['effective_reliability']
            else:
                # Create new metric
                new_metric = ReliabilityMetric(
                    date=yearly_data['date'],
                    period_type='yearly',
                    reliability_score=yearly_data['reliability_score'],
                    testing_compliance=yearly_data['testing_compliance'],
                    inspection_compliance=yearly_data['inspection_compliance'],
                    coverage_ratio=yearly_data['coverage_ratio'],
                    effective_reliability=yearly_data['effective_reliability']
                )
                db.session.add(new_metric)
            
            db.session.commit()
            return True
        return False
    
    @staticmethod
    def process_historical_metrics():
        """Process and store historical monthly and yearly metrics"""
        today = date.today()
        
        # Process monthly metrics for the last 12 months
        for i in range(12):
            target_date = today - timedelta(days=30 * i)
            MetricCalculator.store_monthly_metric(target_date.year, target_date.month)
        
        # Process yearly metrics for the last 5 years
        for i in range(5):
            target_year = today.year - i
            MetricCalculator.store_yearly_metric(target_year)
        
        print("Historical metrics processing completed!")
    
    @staticmethod
    def get_monthly_inspection_compliance(year, month):
        """Calculate monthly inspection compliance for a specific month"""
        # Get the first and last day of the month
        first_day = date(year, month, 1)
        last_day = date(year, month, monthrange(year, month)[1])
        
        # Count substations inspected in this month
        inspected_in_month = db.session.query(func.count(func.distinct(InspectionTest.substation_id))).filter(
            InspectionTest.inspection_date >= first_day,
            InspectionTest.inspection_date <= last_day,
            InspectionTest.inspection_status == "Inspected"
        ).scalar()
        
        # Total substations at the end of the month
        total_substations = Substation.query.filter(
            Substation.created_at <= datetime.combine(last_day, datetime.min.time())
        ).count()
        
        if total_substations == 0:
            return 0
        
        return (inspected_in_month / total_substations) * 100
    
    @staticmethod
    def get_monthly_testing_compliance(year, month):
        """Calculate monthly testing compliance for a specific month"""
        # Get the first and last day of the month
        first_day = date(year, month, 1)
        last_day = date(year, month, monthrange(year, month)[1])
        
        # Count substations tested in this month
        tested_in_month = db.session.query(func.count(func.distinct(InspectionTest.substation_id))).filter(
            InspectionTest.testing_date >= first_day,
            InspectionTest.testing_date <= last_day,
            InspectionTest.testing_status == "Tested"
        ).scalar()
        
        # Total substations at the end of the month
        total_substations = Substation.query.filter(
            Substation.created_at <= datetime.combine(last_day, datetime.min.time())
        ).count()
        
        if total_substations == 0:
            return 0
        
        return (tested_in_month / total_substations) * 100

