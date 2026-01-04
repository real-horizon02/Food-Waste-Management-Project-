"""
Scheduled jobs for Food Tracker
Includes daily expiry alert checks
"""
import schedule
import time
import threading
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from models.grocery_item import GroceryItem
except ImportError:
    try:
        from backend.models.grocery_item import GroceryItem
    except ImportError:
        GroceryItem = None


def check_expiring_items():
    """
    Daily job to check for items expiring within the next 30 days
    Logs alerts to console (can be replaced with push notifications, emails, etc.)
    """
    print("\n" + "="*60)
    print(f"[SCHEDULED JOB] Running expiry check at {datetime.utcnow().isoformat()}")
    print("="*60)
    
    try:
        # Check if GroceryItem model is available and MongoDB is connected
        if not GroceryItem:
            print("[INFO] GroceryItem model not available. Skipping expiry check.")
            print("="*60 + "\n")
            return
        
        now = datetime.utcnow()
        today_30 = now + timedelta(days=30)
        
        # Find items expiring in the next 30 days
        expiring_items = GroceryItem.objects(
            expiryDate__gte=now,
            expiryDate__lte=today_30
        ).order_by('expiryDate')
        
        if not expiring_items:
            print("[INFO] No items expiring in the next 30 days.")
            print("="*60 + "\n")
            return
        
        print(f"[INFO] Found {len(expiring_items)} items expiring in the next 30 days\n")
        
        # Group alerts by user
        alerts_by_user = {}
        for item in expiring_items:
            if item.userEmail not in alerts_by_user:
                alerts_by_user[item.userEmail] = []
            alerts_by_user[item.userEmail].append(item)
        
        # Process alerts for each user
        for user_email, items in alerts_by_user.items():
            print(f"\n[ALERT] Alerts for user: {user_email}")
            print("-" * 60)
            
            for item in items:
                days_left = (item.expiryDate - now).days
                expiry_formatted = item.expiryDate.strftime('%B %d, %Y')
                
                if days_left < 0:
                    status = "EXPIRED"
                    icon = "❌"
                elif days_left == 0:
                    status = "EXPIRES TODAY"
                    icon = "🔴"
                elif days_left <= 3:
                    status = f"CRITICAL ({days_left} days)"
                    icon = "🔴"
                elif days_left <= 7:
                    status = f"SOON ({days_left} days)"
                    icon = "🟠"
                else:
                    status = f"NOTICE ({days_left} days)"
                    icon = "🟡"
                
                print(f"{icon} ALERT: Item [{item.itemName}] for user [{user_email}] is {status}.")
                print(f"   Expiry Date: {expiry_formatted}")
            
            print("-" * 60)
        
        print(f"\n[INFO] Total alerts processed: {len(expiring_items)}")
        print("="*60 + "\n")
        
        # TODO: Here you can add:
        # - Send push notifications
        # - Send emails
        # - Update user dashboard
        # - Call external notification service
        
    except Exception as e:
        # Gracefully handle MongoEngine connection errors and other exceptions
        if "You have not defined a default connection" in str(e):
            print("[INFO] MongoDB connection not initialized. Skipping expiry check.")
        else:
            print(f"[WARN] Warning in expiry check job: {str(e)}")
        print("="*60 + "\n")


def run_scheduler():
    """
    Run the scheduler in a background thread
    """
    print("\n[SCHEDULER] Starting background scheduler...")
    
    # Schedule the job to run every day at 08:00 AM
    schedule.every().day.at("08:00").do(check_expiring_items)
    
    # Also run on startup for immediate testing
    print("[SCHEDULER] Running initial check on startup...")
    check_expiring_items()
    
    print("[SCHEDULER] Scheduler started. Will run daily at 08:00 AM UTC\n")
    
    # Keep the scheduler running
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute if a job needs to run


def start_scheduler_thread():
    """
    Start the scheduler in a daemon thread
    Call this from your Flask app initialization
    """
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    print("[SCHEDULER] Scheduler thread started (running as daemon)")
