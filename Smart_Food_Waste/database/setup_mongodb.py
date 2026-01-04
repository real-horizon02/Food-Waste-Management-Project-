"""
MongoDB setup and connection test script
"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backend', '.env'))

def test_mongodb_connection():
    """Test MongoDB connection"""
    print("="*60)
    print("MongoDB Connection Test")
    print("="*60)
    
    try:
        from mongoengine import connect
        from mongoengine.connection import disconnect
        
        # Get MongoDB URI from environment
        mongo_uri = os.getenv('MONGO_URI', 'mongodb://localhost:27017/smart_waste_db')
        
        print(f"\nAttempting to connect to: {mongo_uri.split('@')[-1] if '@' in mongo_uri else mongo_uri}")
        print("(hiding credentials for security)")
        
        # Disconnect any existing connections
        try:
            disconnect()
        except:
            pass
        
        # Try to connect
        connect(host=mongo_uri, serverSelectionTimeoutMS=5000)
        
        print("✓ MongoDB connection successful!")
        print("\nTesting database operations...")
        
        # Test a simple operation
        from mongoengine import Document, StringField
        from datetime import datetime
        
        class TestDoc(Document):
            name = StringField()
            created = StringField(default=str(datetime.now()))
        
        # Try to create a test document
        test = TestDoc(name="connection_test")
        test.save()
        
        # Verify it was saved
        found = TestDoc.objects(name="connection_test").first()
        if found:
            print("✓ Database write test successful!")
            found.delete()
            print("✓ Database delete test successful!")
        else:
            print("⚠️  Database write test failed")
        
        print("\n" + "="*60)
        print("✅ MongoDB is working correctly!")
        print("="*60)
        return True
        
    except Exception as e:
        print(f"\n❌ MongoDB connection failed!")
        print(f"Error: {str(e)}")
        print("\n" + "="*60)
        print("Troubleshooting:")
        print("="*60)
        print("\n1. Make sure MongoDB service is running:")
        print("   Windows: Check Services (services.msc) for 'MongoDB'")
        print("   Or run: net start MongoDB")
        print("\n2. Check MONGO_URI in backend/.env file:")
        print("   Should be: mongodb://localhost:27017/smart_waste_db")
        print("\n3. Test MongoDB connection manually:")
        print("   Run: mongosh")
        print("   Should connect to MongoDB shell")
        print("\n4. If using MongoDB Atlas (cloud):")
        print("   - Verify connection string in .env")
        print("   - Check IP whitelist includes your IP")
        print("   - Verify username and password")
        print("="*60)
        return False

if __name__ == '__main__':
    test_mongodb_connection()


