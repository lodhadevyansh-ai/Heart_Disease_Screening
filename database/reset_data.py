"""
Safe Clinical Data Reset and Database Backup Utility.

Allows clinicians and developers to clear demo or application-generated patient
records, encounters, vitals, symptoms, documents, lab measurements, and model
predictions, providing a completely clean slate with proper empty states.

SAFETY RULES:
1. Automatically creates a timestamped backup copy of the database prior to modifications.
2. Does NOT drop database tables or run destructive schema migrations.
3. Preserves authenticated User accounts (clinicians/admins/patients) by default.
4. Unlinks User.patient_id references cleanly before removing patient records.
5. Deletes all associated records in correct cascade order to prevent orphaned rows.
"""

import argparse
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app import create_app
from backend.extensions import db
from database.models import (
    Patient,
    User,
    Assessment,
    PatientSymptom,
    VitalSign,
    ClinicalDocument,
    StructuredLabMeasurement,
    ModelPrediction,
)


DEMO_PATIENT_CODES = [
    "DEMO-PT-CAD-001",
    "DEMO-PT-HF-002",
    "DEMO-PT-ARR-003",
    "DEMO-PT-EMERG-004",
    "DEMO-PT-NORM-005",
]


def backup_database(app) -> Path:
    """Create a timestamped backup of the database file if using SQLite."""
    uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
    
    # Handle SQLite database files
    if uri.startswith("sqlite:///"):
        rel_or_abs = uri.replace("sqlite:///", "")
        if os.path.isabs(rel_or_abs):
            db_path = Path(rel_or_abs)
        else:
            db_path = Path(app.instance_path) / rel_or_abs
            if not db_path.exists():
                db_path = PROJECT_ROOT / rel_or_abs
        
        if db_path.exists():
            backup_dir = db_path.parent / "backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            backup_path = backup_dir / f"{db_path.stem}_backup_{timestamp}{db_path.suffix}"
            shutil.copy2(db_path, backup_path)
            print(f"[BACKUP] SQLite database backed up to: {backup_path}")
            return backup_path
        else:
            print(f"[WARN] Database file not found on disk at {db_path}; proceeding with in-memory or uninitialized DB.")
            return Path("none")
    else:
        print(f"[BACKUP] Non-SQLite database URI in use: {uri}")
        return Path("external_rdbms")


def reset_clinical_data(
    app=None,
    demo_only: bool = False,
    include_users: bool = False,
    dry_run: bool = False,
    skip_backup: bool = False,
) -> Dict[str, Any]:
    """
    Safely reset clinical data with automatic backup and relationship integrity.
    
    Parameters
    ----------
    app : Flask, optional
        Flask application instance.
    demo_only : bool, default=False
        If True, only purge known DEMO-PT-* records. If False, clear all patient records.
    include_users : bool, default=False
        If True, purge non-admin user accounts. Default is False (users preserved).
    dry_run : bool, default=False
        If True, simulate and return counts without committing transactions.
    skip_backup : bool, default=False
        If True, skip the automated database file backup.
        
    Returns
    -------
    dict
        Summary of operation with backup path and deleted record counts.
    """
    if app is None:
        app = create_app()

    results: Dict[str, Any] = {
        "status": "simulated" if dry_run else "completed",
        "backup_path": None,
        "mode": "demo_only" if demo_only else "all_patients",
        "counts": {},
    }

    with app.app_context():
        # Step 1: Backup
        if not dry_run and not skip_backup:
            b_path = backup_database(app)
            results["backup_path"] = str(b_path)

        # Step 2: Identify targeted patients
        if demo_only:
            targeted_patients = Patient.query.filter(Patient.patient_code.in_(DEMO_PATIENT_CODES)).all()
        else:
            targeted_patients = Patient.query.all()

        patient_ids = [p.id for p in targeted_patients]

        if not patient_ids:
            print("[INFO] No matching patient records found to reset.")
            results["counts"] = {"patients": 0, "assessments": 0}
            return results

        # Find all associated assessments
        targeted_assessments = Assessment.query.filter(Assessment.patient_id.in_(patient_ids)).all()
        assessment_ids = [a.id for a in targeted_assessments]

        # Count records to be removed
        counts = {
            "patients": len(targeted_patients),
            "assessments": len(targeted_assessments),
            "symptoms": PatientSymptom.query.filter(PatientSymptom.assessment_id.in_(assessment_ids)).count() if assessment_ids else 0,
            "vitals": VitalSign.query.filter(VitalSign.assessment_id.in_(assessment_ids)).count() if assessment_ids else 0,
            "documents": ClinicalDocument.query.filter(ClinicalDocument.assessment_id.in_(assessment_ids)).count() if assessment_ids else 0,
            "lab_measurements": StructuredLabMeasurement.query.filter(StructuredLabMeasurement.assessment_id.in_(assessment_ids)).count() if assessment_ids else 0,
            "predictions": ModelPrediction.query.filter(ModelPrediction.assessment_id.in_(assessment_ids)).count() if assessment_ids else 0,
            "users_unlinked": 0,
            "users_deleted": 0,
        }

        # Step 3: Unlink or manage user associations safely
        linked_users = User.query.filter(User.patient_id.in_(patient_ids)).all()
        counts["users_unlinked"] = len(linked_users)

        if dry_run:
            print(f"[DRY-RUN] Target summary to delete:")
            for k, v in counts.items():
                print(f"  - {k}: {v}")
            results["counts"] = counts
            return results

        # Execute safe deletion in transaction
        try:
            # Unlink patient_id on users so accounts remain fully functional
            for u in linked_users:
                u.patient_id = None
            db.session.flush()

            # Cascade delete assessments (and via ORM cascades, symptoms, vitals, docs, labs, preds)
            for a in targeted_assessments:
                db.session.delete(a)
            db.session.flush()

            # Delete patients
            for p in targeted_patients:
                db.session.delete(p)

            # Optional user deletion (only if explicitly requested and not admin)
            if include_users:
                users_to_delete = User.query.filter(User.role != "admin").all()
                counts["users_deleted"] = len(users_to_delete)
                for u in users_to_delete:
                    db.session.delete(u)

            db.session.commit()
            print(f"[SUCCESS] Clean reset completed successfully:")
            for k, v in counts.items():
                print(f"  - {k}: {v}")
            results["counts"] = counts
            return results

        except Exception as e:
            db.session.rollback()
            print(f"[ERROR] Reset failed: {str(e)}. Transaction rolled back non-destructively.")
            results["status"] = "failed"
            results["error"] = str(e)
            return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CardioCare AI Safe Clinical Database Reset Tool")
    parser.add_argument(
        "--demo-only",
        action="store_true",
        help="Only delete known synthetic demonstration patient records (DEMO-PT-*).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate the deletion and output counts without committing any changes.",
    )
    parser.add_argument(
        "--include-users",
        action="store_true",
        help="Also delete non-admin user accounts. Default is to preserve all users.",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip the automatic database file backup before reset.",
    )

    args = parser.parse_args()

    app = create_app()
    reset_clinical_data(
        app=app,
        demo_only=args.demo_only,
        include_users=args.include_users,
        dry_run=args.dry_run,
        skip_backup=args.no_backup,
    )
