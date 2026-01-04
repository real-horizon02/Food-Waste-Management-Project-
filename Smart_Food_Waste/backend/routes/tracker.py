"""Food Tracker routes for managing grocery items and expiry alerts."""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta

# Import the GroceryItem model (attempt local and package-style imports)
try:
    from models.grocery_item import GroceryItem
    from models.qr_decoded_data import QRDecodedData
except Exception:
    try:
        from backend.models.grocery_item import GroceryItem
        from backend.models.qr_decoded_data import QRDecodedData
    except Exception:
        GroceryItem = None
        QRDecodedData = None

bp = Blueprint('tracker', __name__)


@bp.route('/add-item', methods=['POST'])
def add_item():
    """Add a new grocery item to track.

    Expected JSON body:
    {
        "userEmail": "user@example.com",
        "itemName": "Milk",
        "expiryDate": "2025-12-25",  # ISO or YYYY-MM-DD
        "productCode": "5901234123457",  # Optional: EAN/UPC
        "scannedFromQR": true  # Optional: Whether scanned from QR
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        user_email = data.get('userEmail')
        item_name = data.get('itemName')
        expiry_date_str = data.get('expiryDate')
        product_code = data.get('productCode', '')
        scanned_from_qr = data.get('scannedFromQR', False)

        if not user_email or not item_name or not expiry_date_str:
            return jsonify({'error': 'Missing required fields: userEmail, itemName, expiryDate'}), 400

        # Parse expiry date
        try:
            if 'T' in expiry_date_str:
                expiry_date = datetime.fromisoformat(expiry_date_str.replace('Z', '+00:00'))
            else:
                expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d')
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD or ISO format'}), 400

        if GroceryItem is None:
            return jsonify({'error': 'GroceryItem model not available'}), 500

        grocery_item = GroceryItem(
            userEmail=user_email,
            itemName=item_name,
            productCode=product_code if product_code else None,
            scannedFromQR=scanned_from_qr,
            expiryDate=expiry_date,
            purchaseDate=datetime.utcnow(),
        )
        grocery_item.save()

        return jsonify({'message': 'Item added successfully', 'item': grocery_item.to_dict()}), 201

    except Exception as e:
        print(f"[ERR] Error adding item: {e}")
        return jsonify({'error': f'Server error: {e}'}), 500


@bp.route('/items', methods=['GET'])
def get_items():
    """Get all tracked items for a user (filtered by userEmail query parameter)."""
    try:
        user_email = request.args.get('userEmail')
        if not user_email:
            return jsonify({'error': 'userEmail query parameter required'}), 400

        items = GroceryItem.objects(userEmail=user_email).order_by('-expiryDate')

        expired_items = []
        expiring_soon = []
        active_items = []

        for item in items:
            item_dict = item.to_dict()
            item_dict['daysUntilExpiry'] = item.days_until_expiry()
            if item.is_expired():
                expired_items.append(item_dict)
            elif item.is_expiring_soon(30):
                expiring_soon.append(item_dict)
            else:
                active_items.append(item_dict)

        return jsonify({
            'userEmail': user_email,
            'total': len(items),
            'expired': len(expired_items),
            'expiringSoon': len(expiring_soon),
            'active': len(active_items),
            'expiredItems': expired_items,
            'expiringItems': expiring_soon,
            'activeItems': active_items,
        }), 200

    except Exception as e:
        print(f"[ERR] Error fetching items: {e}")
        return jsonify({'error': f'Server error: {e}'}), 500


@bp.route('/items/<item_id>', methods=['DELETE'])
def delete_item(item_id):
    """Delete a tracked item."""
    try:
        grocery_item = GroceryItem.objects(id=item_id).first()
        if not grocery_item:
            return jsonify({'error': 'Item not found'}), 404
        grocery_item.delete()
        return jsonify({'message': 'Item deleted successfully'}), 200
    except Exception as e:
        print(f"[ERR] Error deleting item: {e}")
        return jsonify({'error': f'Server error: {e}'}), 500


@bp.route('/items/<item_id>', methods=['PUT'])
def update_item(item_id):
    """Update a tracked item.

    Expected JSON body:
    {
        "itemName": "Milk",
        "expiryDate": "2025-12-25"
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        grocery_item = GroceryItem.objects(id=item_id).first()
        if not grocery_item:
            return jsonify({'error': 'Item not found'}), 404

        if 'itemName' in data:
            grocery_item.itemName = data['itemName']

        if 'expiryDate' in data:
            try:
                expiry_date_str = data['expiryDate']
                if 'T' in expiry_date_str:
                    grocery_item.expiryDate = datetime.fromisoformat(expiry_date_str.replace('Z', '+00:00'))
                else:
                    grocery_item.expiryDate = datetime.strptime(expiry_date_str, '%Y-%m-%d')
            except ValueError:
                return jsonify({'error': 'Invalid date format'}), 400

        grocery_item.updated_at = datetime.utcnow()
        grocery_item.save()
        return jsonify({'message': 'Item updated successfully', 'item': grocery_item.to_dict()}), 200

    except Exception as e:
        print(f"[ERR] Error updating item: {e}")
        return jsonify({'error': f'Server error: {e}'}), 500


@bp.route('/alerts/expiring-soon', methods=['GET'])
def get_expiring_alerts():
    """Get all items expiring within the next 30 days for all users."""
    try:
        now = datetime.utcnow()
        today_30 = now + timedelta(days=30)

        expiring_items = GroceryItem.objects(
            expiryDate__gte=now,
            expiryDate__lte=today_30
        ).order_by('expiryDate')

        alerts_by_user = {}
        for item in expiring_items:
            alerts_by_user.setdefault(item.userEmail, []).append(item.to_dict())

        return jsonify({
            'timestamp': datetime.utcnow().isoformat(),
            'totalAlerts': len(expiring_items),
            'usersWithAlerts': len(alerts_by_user),
            'alertsByUser': alerts_by_user,
        }), 200

    except Exception as e:
        print(f"[ERR] Error fetching alerts: {e}")
        return jsonify({'error': f'Server error: {e}'}), 500


@bp.route('/product-info', methods=['POST'])
def get_product_info():
    """Get product information from EAN/barcode.
    
    Expected JSON body:
    {
        "ean": "5901234123457"
    }
    
    This endpoint can be extended to integrate with external product databases
    like Open Food Facts API (https://world.openfoodfacts.org/api)
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        ean = data.get('ean', '').strip()
        if not ean:
            return jsonify({'error': 'EAN/Barcode is required'}), 400
        
        # Try to fetch from Open Food Facts API
        import requests
        try:
            response = requests.get(
                f'https://world.openfoodfacts.org/api/v0/product/{ean}.json',
                timeout=5
            )
            
            if response.status_code == 200:
                product_data = response.json()
                if product_data.get('status') == 1:
                    product = product_data.get('product', {})
                    return jsonify({
                        'product_name': product.get('product_name', 'Unknown Product'),
                        'brand': product.get('brands', ''),
                        'image_url': product.get('image_front_url', ''),
                        'ean': ean
                    }), 200
        except requests.RequestException:
            pass  # Fall through to local search
        
        # If not found in Open Food Facts, return generic response
        # Users can still add items manually
        return jsonify({
            'error': 'Product not found in database',
            'ean': ean
        }), 404
        
    except Exception as e:
        print(f"[ERR] Error fetching product info: {e}")
        return jsonify({'error': f'Server error: {e}'}), 500


@bp.route('/qr-decoded-data', methods=['POST'])
@jwt_required()
def save_qr_decoded_data():
    """Save decoded QR code data to database.
    
    Expected JSON body:
    {
        "rawQRCode": "...",
        "ean": "5901234123457",
        "productName": "Product Name",
        "batchCode": "B123456",
        "serialNumber": "SN789",
        "expiryDate": "2024-12-31",
        "detectedFormat": "GS1"
    }
    """
    try:
        user_email = get_jwt_identity()
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Validate required fields
        if not data.get('rawQRCode'):
            return jsonify({'error': 'rawQRCode is required'}), 400
        
        expiry_date = None
        if data.get('expiryDate'):
            try:
                expiry_date_str = data['expiryDate']
                if isinstance(expiry_date_str, str):
                    if 'T' in expiry_date_str:
                        expiry_date = datetime.fromisoformat(expiry_date_str.replace('Z', '+00:00'))
                    else:
                        expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d')
                else:
                    expiry_date = expiry_date_str
            except (ValueError, TypeError) as e:
                print(f"[WARN] Invalid expiry date format: {e}")
        
        # Calculate derived fields
        days_until_expiry = None
        is_expired = False
        expiry_status = 'unknown'
        
        if expiry_date:
            now = datetime.utcnow()
            if expiry_date.tzinfo:
                now = now.replace(tzinfo=expiry_date.tzinfo)
            
            days_until_expiry = (expiry_date.date() if hasattr(expiry_date, 'date') else expiry_date) - (now.date() if hasattr(now, 'date') else now)
            if isinstance(days_until_expiry, timedelta):
                days_until_expiry = days_until_expiry.days
            
            is_expired = days_until_expiry < 0
            
            if is_expired:
                expiry_status = 'expired'
            elif days_until_expiry <= 3:
                expiry_status = 'critical'
            elif days_until_expiry <= 7:
                expiry_status = 'warning'
            elif days_until_expiry <= 30:
                expiry_status = 'expiring_soon'
            else:
                expiry_status = 'active'
        
        # Create QRDecodedData document
        qr_data = QRDecodedData(
            userEmail=user_email,
            rawQRCode=data.get('rawQRCode'),
            ean=data.get('ean'),
            productName=data.get('productName'),
            batchCode=data.get('batchCode'),
            serialNumber=data.get('serialNumber'),
            expiryDate=expiry_date,
            daysUntilExpiry=days_until_expiry,
            isExpired=is_expired,
            expiryStatus=expiry_status,
            detectedFormat=data.get('detectedFormat', 'unknown')
        )
        
        qr_data.save()
        
        print(f"[INFO] Saved QR data for {user_email}: {qr_data.id}")
        
        return jsonify({
            'message': 'QR data saved successfully',
            'qrDataId': str(qr_data.id),
            'data': qr_data.to_dict()
        }), 201
        
    except Exception as e:
        print(f"[ERR] Error saving QR decoded data: {e}")
        return jsonify({'error': f'Server error: {e}'}), 500


@bp.route('/qr-alerts', methods=['GET'])
@jwt_required()
def get_qr_alerts():
    """Get all QR decoded data alerts for current user.
    
    Supports filtering by:
    - status: 'expired', 'critical', 'warning', 'expiring_soon', 'active'
    - days_limit: only items expiring within N days (default 30)
    
    Query parameters:
    - ?status=expiring_soon
    - ?days_limit=14
    """
    try:
        user_email = get_jwt_identity()
        status = request.args.get('status')  # Optional filter
        days_limit = request.args.get('days_limit', default=30, type=int)
        
        # Build query
        query = QRDecodedData.objects(userEmail=user_email)
        
        # Apply status filter if provided
        if status:
            query = query(expiryStatus=status)
        else:
            # Default: get all non-active items (expired, critical, warning, expiring_soon)
            query = query(expiryStatus__in=['expired', 'critical', 'warning', 'expiring_soon'])
        
        # Apply days limit filter if not explicitly showing all
        if days_limit:
            now = datetime.utcnow()
            future_date = now + timedelta(days=days_limit)
            query = query(expiryDate__lte=future_date)
        
        # Sort by expiry date (soonest first)
        alerts = query.order_by('expiryDate', '-daysUntilExpiry')
        
        alerts_list = [alert.to_dict() for alert in alerts]
        
        # Group by status for better UI
        alerts_by_status = {}
        for alert in alerts_list:
            status = alert['expiryStatus']
            alerts_by_status.setdefault(status, []).append(alert)
        
        return jsonify({
            'timestamp': datetime.utcnow().isoformat(),
            'userEmail': user_email,
            'totalAlerts': len(alerts_list),
            'alertsByStatus': alerts_by_status,
            'alerts': alerts_list
        }), 200
        
    except Exception as e:
        print(f"[ERR] Error fetching QR alerts: {e}")
        return jsonify({'error': f'Server error: {e}'}), 500


@bp.route('/qr-decoded-data/<data_id>', methods=['GET'])
@jwt_required()
def get_qr_decoded_data(data_id):
    """Get a specific QR decoded data entry."""
    try:
        user_email = get_jwt_identity()
        
        try:
            from bson.objectid import ObjectId
            qr_data = QRDecodedData.objects.get(id=ObjectId(data_id), userEmail=user_email)
        except:
            qr_data = QRDecodedData.objects.get(id=data_id, userEmail=user_email)
        
        return jsonify({
            'data': qr_data.to_dict()
        }), 200
        
    except QRDecodedData.DoesNotExist:
        return jsonify({'error': 'QR data not found'}), 404
    except Exception as e:
        print(f"[ERR] Error fetching QR data: {e}")
        return jsonify({'error': f'Server error: {e}'}), 500


@bp.route('/qr-decoded-data/<data_id>', methods=['DELETE'])
@jwt_required()
def delete_qr_decoded_data(data_id):
    """Delete a specific QR decoded data entry."""
    try:
        user_email = get_jwt_identity()
        
        try:
            from bson.objectid import ObjectId
            qr_data = QRDecodedData.objects.get(id=ObjectId(data_id), userEmail=user_email)
        except:
            qr_data = QRDecodedData.objects.get(id=data_id, userEmail=user_email)
        
        qr_data.delete()
        
        return jsonify({'message': 'QR data deleted successfully'}), 200
        
    except QRDecodedData.DoesNotExist:
        return jsonify({'error': 'QR data not found'}), 404
    except Exception as e:
        print(f"[ERR] Error deleting QR data: {e}")
        return jsonify({'error': f'Server error: {e}'}), 500

