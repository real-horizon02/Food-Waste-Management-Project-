"""QR Code Decoded Data model for storing extracted product information."""

from datetime import datetime
from mongoengine import Document, StringField, EmailField, DateTimeField, IntField, BooleanField


class QRDecodedData(Document):
    """Stores decoded QR code data including extracted product information."""

    # User association
    userEmail = EmailField(required=True)

    # Raw data
    rawQRCode = StringField(required=True, max_length=500)

    # Extracted GS1 Data
    ean = StringField(max_length=50)  # GTIN/EAN
    productName = StringField(max_length=200)
    batchCode = StringField(max_length=100)
    serialNumber = StringField(max_length=100)

    # Expiry Information
    expiryDate = DateTimeField()
    daysUntilExpiry = IntField()
    isExpired = BooleanField(default=False)
    expiryStatus = StringField(
        max_length=20,
        choices=['expired', 'critical', 'warning', 'expiring_soon', 'active'],
        default='active'
    )

    # QR Code Format Detection
    detectedFormat = StringField(
        max_length=50,
        choices=['GS1', 'EAN', 'GTIN', 'QR_CODE', 'UNKNOWN'],
        default='UNKNOWN'
    )

    # Metadata
    scannedAt = DateTimeField(default=datetime.utcnow)
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)

    meta = {
        'collection': 'qr_decoded_data',
        'indexes': [
            'userEmail',
            'ean',
            'expiryDate',
            ('userEmail', 'expiryDate'),  # Compound index for expiry queries
            ('userEmail', 'expiryStatus'),  # For filtering by status
        ],
    }

    def to_dict(self):
        """Return a JSON-serializable representation of the document."""
        return {
            'id': str(self.id),
            'userEmail': self.userEmail,
            'rawQRCode': self.rawQRCode,
            'ean': self.ean,
            'productName': self.productName,
            'batchCode': self.batchCode,
            'serialNumber': self.serialNumber,
            'expiryDate': self.expiryDate.isoformat() if self.expiryDate else None,
            'daysUntilExpiry': self.daysUntilExpiry,
            'isExpired': self.isExpired,
            'expiryStatus': self.expiryStatus,
            'detectedFormat': self.detectedFormat,
            'scannedAt': self.scannedAt.isoformat() if self.scannedAt else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    @staticmethod
    def calculate_expiry_status(days_until_expiry):
        """Calculate expiry status based on days until expiry."""
        if days_until_expiry < 0:
            return 'expired'
        elif days_until_expiry <= 3:
            return 'critical'
        elif days_until_expiry <= 7:
            return 'warning'
        elif days_until_expiry <= 30:
            return 'expiring_soon'
        else:
            return 'active'
