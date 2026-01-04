"""GroceryItem model for Food Tracker (MongoDB / MongoEngine).

This module defines the GroceryItem document used by the Food Tracker
feature. It stores a user's grocery items with purchase/expiry dates and
provides convenience helpers for expiry calculations.
"""

from datetime import datetime

from mongoengine import Document, StringField, EmailField, DateTimeField, BooleanField


class GroceryItem(Document):
    """Food Tracker model for storing grocery items with expiry dates."""

    # User email - used to associate items with users
    userEmail = EmailField(required=True)

    # Item details
    itemName = StringField(required=True, max_length=100)
    productCode = StringField(max_length=50)  # EAN/UPC barcode
    scannedFromQR = BooleanField(default=False)  # Whether scanned from QR code

    # Tracking dates
    purchaseDate = DateTimeField(default=datetime.utcnow)
    expiryDate = DateTimeField(required=True)

    # Metadata
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)

    meta = {
        'collection': 'grocery_items',
        'indexes': [
            'userEmail',
            'expiryDate',
            ('userEmail', 'expiryDate'),  # Compound index for efficient queries
        ],
    }

    def to_dict(self):
        """Return a JSON-serializable representation of the document."""
        return {
            'id': str(self.id),
            'userEmail': self.userEmail,
            'itemName': self.itemName,
            'productCode': self.productCode or None,
            'scannedFromQR': self.scannedFromQR,
            'purchaseDate': self.purchaseDate.isoformat() if self.purchaseDate else None,
            'expiryDate': self.expiryDate.isoformat() if self.expiryDate else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    def days_until_expiry(self):
        """Return number of whole days until expiry (may be negative).

        Returns an int or None if `expiryDate` is not set.
        """
        if not self.expiryDate:
            return None
        delta = self.expiryDate - datetime.utcnow()
        return delta.days

    def is_expired(self):
        """Return True if the item is already expired."""
        if not self.expiryDate:
            return False
        return datetime.utcnow() > self.expiryDate

    def is_expiring_soon(self, days=30):
        """Return True if the item will expire within `days` days (exclusive of expiry=0).

        days argument defaults to 30.
        """
        days_left = self.days_until_expiry()
        if days_left is None:
            return False
        return 0 < days_left <= days
