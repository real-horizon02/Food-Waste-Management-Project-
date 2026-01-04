/**
 * Test the expiry popup functionality
 * Open browser console and run: testExpiryPopup()
 */

function testExpiryPopup() {
  console.log('Testing expiry popup...');
  
  // Mock data for testing
  const mockExpiringItems = [
    {
      id: '1',
      itemName: 'Milk',
      expiryDate: new Date(Date.now() + 2 * 24 * 60 * 60 * 1000).toISOString(), // 2 days
      daysUntilExpiry: 2
    },
    {
      id: '2',
      itemName: 'Chicken Breast',
      expiryDate: new Date(Date.now() + 1 * 24 * 60 * 60 * 1000).toISOString(), // 1 day
      daysUntilExpiry: 1
    },
    {
      id: '3',
      itemName: 'Vegetables Pack',
      expiryDate: new Date(Date.now() + 5 * 24 * 60 * 60 * 1000).toISOString(), // 5 days
      daysUntilExpiry: 5
    }
  ];
  
  // Display the popup with mock data
  displayExpiryPopup(mockExpiringItems);
  console.log('Popup displayed with mock data');
}

// Alternative: Test the actual API call
async function testExpiryPopupLive() {
  console.log('Testing expiry popup with live data...');
  await checkAndShowExpiryPopup();
}
