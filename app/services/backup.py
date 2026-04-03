"""
Disaster Recovery Service.

Provides:
- Automated database backups
- Point-in-time recovery
- Backup verification
- Cloud storage integration (optional)
"""

import hashlib
import logging
import os
import shutil
import subprocess
import gzip
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any

from app.core.config import settings


logger = logging.getLogger(__name__)


class BackupInfo:
    """Information about a backup."""
    
    def __init__(
        self,
        filename: str,
        filepath: Path,
        created_at: datetime,
        size_bytes: int,
        checksum: str,
        compressed: bool = True,
    ):
        self.filename = filename
        self.filepath = filepath
        self.created_at = created_at
        self.size_bytes = size_bytes
        self.checksum = checksum
        self.compressed = compressed
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "filename": self.filename,
            "filepath": str(self.filepath),
            "created_at": self.created_at.isoformat(),
            "size_bytes": self.size_bytes,
            "size_human": self._human_size(),
            "checksum": self.checksum,
            "compressed": self.compressed,
        }
    
    def _human_size(self) -> str:
        for unit in ["B", "KB", "MB", "GB"]:
            if self.size_bytes < 1024:
                return f"{self.size_bytes:.1f} {unit}"
            self.size_bytes /= 1024
        return f"{self.size_bytes:.1f} TB"


class DisasterRecoveryService:
    """
    Disaster recovery and backup management.
    
    Features:
    - SQLite database backups with compression
    - Retention policy (keep last N backups)
    - Checksum verification
    - Scheduled backup support
    """
    
    def __init__(
        self,
        backup_dir: Optional[Path] = None,
        retention_days: int = 30,
        retention_count: int = 10,
    ):
        self.backup_dir = backup_dir or Path(settings.BACKUP_DIR)
        self.retention_days = retention_days
        self.retention_count = retention_count
        
        # Create backup directory
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def _compute_checksum(self, filepath: Path) -> str:
        """Compute SHA256 checksum of a file."""
        sha256 = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    def _get_db_path(self) -> Path:
        """Get the database file path from settings."""
        # Extract path from SQLite URL
        db_url = settings.database_url
        if "sqlite:///" in db_url:
            return Path(db_url.replace("sqlite:///", ""))
        return Path("data/opencredit.db")
    
    def create_backup(
        self,
        compress: bool = True,
        label: Optional[str] = None,
    ) -> Optional[BackupInfo]:
        """
        Create a database backup.
        
        Args:
            compress: Whether to gzip the backup
            label: Optional label to include in filename
            
        Returns:
            BackupInfo if successful, None otherwise
        """
        try:
            db_path = self._get_db_path()
            
            if not db_path.exists():
                logger.error(f"Database file not found: {db_path}")
                return None
            
            # Generate filename
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            label_part = f"_{label}" if label else ""
            ext = ".db.gz" if compress else ".db"
            filename = f"backup_{timestamp}{label_part}{ext}"
            backup_path = self.backup_dir / filename
            
            # Create backup
            if compress:
                with open(db_path, "rb") as f_in:
                    with gzip.open(backup_path, "wb") as f_out:
                        shutil.copyfileobj(f_in, f_out)
            else:
                shutil.copy2(db_path, backup_path)
            
            # Compute checksum
            checksum = self._compute_checksum(backup_path)
            
            # Create backup info
            backup_info = BackupInfo(
                filename=filename,
                filepath=backup_path,
                created_at=datetime.utcnow(),
                size_bytes=backup_path.stat().st_size,
                checksum=checksum,
                compressed=compress,
            )
            
            # Save checksum file
            checksum_file = backup_path.with_suffix(backup_path.suffix + ".sha256")
            checksum_file.write_text(f"{checksum}  {filename}")
            
            logger.info(f"Backup created: {filename} ({backup_info._human_size()})")
            
            # Apply retention policy
            self._apply_retention_policy()
            
            return backup_info
            
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            return None
    
    def restore_backup(
        self,
        backup_path: Path,
        verify_checksum: bool = True,
    ) -> bool:
        """
        Restore database from a backup.
        
        Args:
            backup_path: Path to the backup file
            verify_checksum: Whether to verify checksum before restore
            
        Returns:
            True if successful
        """
        try:
            if not backup_path.exists():
                logger.error(f"Backup file not found: {backup_path}")
                return False
            
            # Verify checksum if requested
            if verify_checksum:
                checksum_file = backup_path.with_suffix(backup_path.suffix + ".sha256")
                if checksum_file.exists():
                    expected = checksum_file.read_text().split()[0]
                    actual = self._compute_checksum(backup_path)
                    if expected != actual:
                        logger.error("Checksum verification failed!")
                        return False
            
            db_path = self._get_db_path()
            
            # Create backup of current database
            if db_path.exists():
                pre_restore_backup = db_path.with_suffix(".pre_restore.db")
                shutil.copy2(db_path, pre_restore_backup)
                logger.info(f"Pre-restore backup: {pre_restore_backup}")
            
            # Restore
            if backup_path.suffix == ".gz" or str(backup_path).endswith(".db.gz"):
                with gzip.open(backup_path, "rb") as f_in:
                    with open(db_path, "wb") as f_out:
                        shutil.copyfileobj(f_in, f_out)
            else:
                shutil.copy2(backup_path, db_path)
            
            logger.info(f"Database restored from: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Restore failed: {e}")
            return False
    
    def list_backups(self) -> List[BackupInfo]:
        """List all available backups."""
        backups = []
        
        for filepath in sorted(self.backup_dir.glob("backup_*.db*"), reverse=True):
            # Skip checksum files
            if filepath.suffix == ".sha256":
                continue
            
            # Get checksum
            checksum = ""
            checksum_file = filepath.with_suffix(filepath.suffix + ".sha256")
            if checksum_file.exists():
                checksum = checksum_file.read_text().split()[0]
            
            # Parse timestamp from filename
            try:
                parts = filepath.stem.replace("backup_", "").split("_")
                date_str = parts[0]
                time_str = parts[1] if len(parts) > 1 else "000000"
                created_at = datetime.strptime(f"{date_str}_{time_str}", "%Y%m%d_%H%M%S")
            except (ValueError, IndexError):
                created_at = datetime.fromtimestamp(filepath.stat().st_mtime)
            
            backups.append(BackupInfo(
                filename=filepath.name,
                filepath=filepath,
                created_at=created_at,
                size_bytes=filepath.stat().st_size,
                checksum=checksum,
                compressed=".gz" in filepath.suffix or str(filepath).endswith(".db.gz"),
            ))
        
        return backups
    
    def verify_backup(self, backup_path: Path) -> Dict[str, Any]:
        """
        Verify a backup's integrity.
        
        Returns:
            Verification result with status and details
        """
        result = {
            "valid": False,
            "checksum_verified": False,
            "readable": False,
            "errors": [],
        }
        
        if not backup_path.exists():
            result["errors"].append("Backup file not found")
            return result
        
        # Verify checksum
        checksum_file = backup_path.with_suffix(backup_path.suffix + ".sha256")
        if checksum_file.exists():
            expected = checksum_file.read_text().split()[0]
            actual = self._compute_checksum(backup_path)
            result["checksum_verified"] = (expected == actual)
            if not result["checksum_verified"]:
                result["errors"].append("Checksum mismatch")
        else:
            result["errors"].append("No checksum file found")
        
        # Try to read the backup
        try:
            import tempfile
            import sqlite3
            
            with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
                tmp_path = tmp.name
            
            try:
                # Decompress if needed
                if ".gz" in str(backup_path):
                    with gzip.open(backup_path, "rb") as f_in:
                        with open(tmp_path, "wb") as f_out:
                            shutil.copyfileobj(f_in, f_out)
                else:
                    shutil.copy2(backup_path, tmp_path)
                
                # Try to connect and run integrity check
                conn = sqlite3.connect(tmp_path)
                cursor = conn.cursor()
                cursor.execute("PRAGMA integrity_check")
                integrity = cursor.fetchone()[0]
                
                if integrity == "ok":
                    result["readable"] = True
                else:
                    result["errors"].append(f"Integrity check failed: {integrity}")
                
                # Count tables
                cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
                result["table_count"] = cursor.fetchone()[0]
                
                conn.close()
                
            finally:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                
        except Exception as e:
            result["errors"].append(f"Failed to read backup: {e}")
        
        result["valid"] = result["checksum_verified"] and result["readable"]
        return result
    
    def _apply_retention_policy(self) -> int:
        """
        Apply retention policy to old backups.
        
        Returns:
            Number of backups deleted
        """
        backups = self.list_backups()
        deleted = 0
        cutoff_date = datetime.utcnow() - timedelta(days=self.retention_days)
        
        for i, backup in enumerate(backups):
            should_delete = False
            
            # Delete if too old
            if backup.created_at < cutoff_date:
                should_delete = True
            
            # Delete if exceeds count (keep most recent)
            if i >= self.retention_count:
                should_delete = True
            
            if should_delete:
                try:
                    backup.filepath.unlink()
                    # Delete checksum file too
                    checksum_file = backup.filepath.with_suffix(backup.filepath.suffix + ".sha256")
                    if checksum_file.exists():
                        checksum_file.unlink()
                    deleted += 1
                    logger.info(f"Deleted old backup: {backup.filename}")
                except Exception as e:
                    logger.error(f"Failed to delete backup {backup.filename}: {e}")
        
        return deleted
    
    def get_storage_usage(self) -> Dict[str, Any]:
        """Get backup storage usage statistics."""
        backups = self.list_backups()
        total_size = sum(b.size_bytes for b in backups)
        
        return {
            "backup_count": len(backups),
            "total_size_bytes": total_size,
            "total_size_human": self._format_size(total_size),
            "oldest_backup": backups[-1].created_at.isoformat() if backups else None,
            "newest_backup": backups[0].created_at.isoformat() if backups else None,
            "retention_days": self.retention_days,
            "retention_count": self.retention_count,
        }
    
    def _format_size(self, size_bytes: int) -> str:
        """Format bytes to human-readable size."""
        for unit in ["B", "KB", "MB", "GB"]:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"


# Singleton instance
backup_service = DisasterRecoveryService()
