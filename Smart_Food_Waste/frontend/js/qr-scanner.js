/**
 * QR Code Scanner for Food Tracker (Mobile & Desktop Friendly)
 * Uses native camera API with jsQR for barcode/QR code scanning
 * Requests explicit camera permission
 */

let videoStream = null;
let scannerActive = false;
let scanningInterval = null;
let lastScannedQRData = null; // Store parsed QR data for backend submission

/**
 * Switch between manual and QR code tabs
 */
window.switchTrackerTab = function(tab) {
  const manualContainer = document.getElementById('tracker-manual-form-container');
  const qrContainer = document.getElementById('tracker-qr-form-container');
  const manualTab = document.getElementById('tracker-tab-manual');
  const qrTab = document.getElementById('tracker-tab-qr');
  
  if (tab === 'manual') {
    manualContainer.style.display = 'block';
    qrContainer.style.display = 'none';
    manualTab.classList.add('active');
    qrTab.classList.remove('active');
    stopQrScanner();
  } else if (tab === 'qr') {
    manualContainer.style.display = 'none';
    qrContainer.style.display = 'block';
    manualTab.classList.remove('active');
    qrTab.classList.add('active');
    setTimeout(() => startQrScanner(), 200);
  }
};

/**
 * Request camera permission and start scanner
 */
async function startQrScanner() {
  if (scannerActive) return;
  
  try {
    const scannerDiv = document.getElementById('qr-scanner');
    if (!scannerDiv) {
      showError('Scanner container not found');
      return;
    }
    
    // Show permission request message
    showLoading();
    console.log('Requesting camera permission...');
    
    // Request camera permission
    const stream = await navigator.mediaDevices.getUserMedia({
      video: {
        facingMode: { ideal: 'environment' },
        width: { ideal: 1280 },
        height: { ideal: 720 }
      },
      audio: false
    });
    
    hideLoading();
    
    videoStream = stream;
    scannerActive = true;
    
    // Create video element
    const video = document.createElement('video');
    video.id = 'qr-video';
    video.srcObject = stream;
    video.style.width = '100%';
    video.style.height = '100%';
    video.style.objectFit = 'cover';
    video.setAttribute('playsinline', 'true');
    video.setAttribute('autoplay', 'true');
    video.muted = true;
    
    // Create canvas for processing
    const canvas = document.createElement('canvas');
    canvas.id = 'qr-canvas';
    canvas.style.display = 'none';
    
    // Clear and append elements
    scannerDiv.innerHTML = '';
    scannerDiv.appendChild(video);
    scannerDiv.appendChild(canvas);
    
    // Wait for video to be ready
    await new Promise(resolve => {
      video.onloadedmetadata = () => {
        video.play();
        resolve();
      };
    });
    
    console.log('✅ Camera started successfully!');
    showSuccess('📷 Camera activated! Position barcode/QR code in view');
    
    // Start scanning loop
    startScanningLoop(video, canvas);
    
  } catch (error) {
    hideLoading();
    console.error('Camera error:', error);
    scannerActive = false;
    videoStream = null;
    
    // Friendly error messages
    if (error.name === 'NotAllowedError') {
      showError('❌ Camera permission denied.\n\nTo enable:\n1. Check browser permissions\n2. Look for 🔒 icon in address bar\n3. Click "Allow" for camera access');
    } else if (error.name === 'NotFoundError') {
      showError('❌ No camera device found.\n\nPlease make sure your device has a camera.');
    } else if (error.name === 'NotReadableError') {
      showError('❌ Camera is already in use.\n\nClose other apps/tabs using the camera and try again.');
    } else if (error.name === 'OverconstrainedError') {
      showError('❌ Camera does not support required settings.\n\nTry a different browser or device.');
    } else {
      showError('❌ Camera access failed: ' + error.message);
    }
  }
}

/**
 * Scanning loop using jsQR
 */
function startScanningLoop(video, canvas) {
  const canvasContext = canvas.getContext('2d', { willReadFrequently: true });
  
  const scanFrame = () => {
    if (!scannerActive) return;
    
    // Set canvas size to match video
    if (canvas.width !== video.videoWidth) {
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
    }
    
    // Draw video frame to canvas
    canvasContext.drawImage(video, 0, 0, canvas.width, canvas.height);
    
    // Get image data
    const imageData = canvasContext.getImageData(0, 0, canvas.width, canvas.height);
    
    // Check if jsQR is available and scan
    if (typeof jsQR !== 'undefined') {
      const code = jsQR(imageData.data, imageData.width, imageData.height, {
        inversionAttempts: 'dontInvert'
      });
      
      if (code) {
        console.log('✅ Code detected:', code.data);
        handleQrDetected(code.data);
        return; // Stop scanning after detection
      }
    }
    
    // Continue scanning
    scanningInterval = requestAnimationFrame(scanFrame);
  };
  
  scanningInterval = requestAnimationFrame(scanFrame);
}

/**
 * Handle detected QR/barcode
 */
function handleQrDetected(code) {
  stopQrScanner();
  console.log('Processing detected code:', code);
  
  // Try to parse the code for embedded data (JSON, GS1, EAN, etc)
  const parsedData = parseQrCodeData(code);
  console.log('Parsed data:', parsedData);
  
  // Store the parsed data globally for later submission to backend
  lastScannedQRData = {
    rawQRCode: code,
    ...parsedData,
    detectedFormat: parsedData.format || 'QR_CODE'
  };
  
  // If expiry date found in QR code, use it
  if (parsedData.expiryDate) {
    console.log('✅ Found expiry date in QR:', parsedData.expiryDate);
    populateQrForm(
      parsedData.ean || code,
      parsedData.productName || 'Scanned Product',
      parsedData.ean || code,
      parsedData.expiryDate
    );
    showSuccess('✅ Product details extracted from QR code!');
    
    // Check if already expired or expiring soon
    checkExpiryAlert(parsedData.expiryDate);
  } else if (parsedData.ean || parsedData.productName) {
    // If we have EAN or product name but no expiry, fetch product info
    console.log('Found product info but no expiry date, asking user to enter it');
    populateQrForm(
      parsedData.ean || code,
      parsedData.productName || 'Scanned Product',
      parsedData.ean || code,
      null
    );
    showSuccess('✅ Product found! Please enter expiry date.');
  } else {
    // Fallback: try to fetch product info from backend using raw code
    console.log('No parsed data found, attempting backend product lookup');
    fetchProductInfo(code);
  }
}

/**
 * Parse QR code data for embedded product information
 * Supports JSON format, GS1-128, GS1 DataMatrix, and other formats
 */
function parseQrCodeData(code) {
  const result = {
    ean: null,
    productName: null,
    expiryDate: null,
    batchCode: null,
    serialNumber: null
  };
  
  // First, try to parse as JSON (for custom QR codes with product data)
  try {
    const jsonData = JSON.parse(code);
    console.log('✅ JSON format detected:', jsonData);
    
    // Extract fields from JSON if they exist
    if (jsonData.productId) result.ean = jsonData.productId;
    if (jsonData.itemName) result.productName = jsonData.itemName;
    if (jsonData.expiryDate) result.expiryDate = jsonData.expiryDate;
    if (jsonData.batchCode) result.batchCode = jsonData.batchCode;
    if (jsonData.serialNumber) result.serialNumber = jsonData.serialNumber;
    
    // Alternative field names
    if (!result.ean && jsonData.ean) result.ean = jsonData.ean;
    if (!result.ean && jsonData.barcode) result.ean = jsonData.barcode;
    if (!result.productName && jsonData.name) result.productName = jsonData.name;
    if (!result.productName && jsonData.productName) result.productName = jsonData.productName;
    
    console.log('Parsed JSON result:', result);
    if (result.expiryDate || result.ean || result.productName) {
      return result; // Found useful data in JSON
    }
  } catch (e) {
    // Not JSON, continue with other formats
    console.log('Not JSON format, trying other formats...');
  }
  
  // GS1 AI 17 = Expiry Date (YYMMDD format)
  // Format: (17)YYMMDD
  const expiry17Match = code.match(/\(17\)(\d{6})/);
  if (expiry17Match) {
    result.expiryDate = parseGS1Date(expiry17Match[1]);
    console.log('Found GS1 AI-17 expiry:', result.expiryDate);
  }
  
  // Alternative GS1 AI 15 = Best Before Date (YYMMDD)
  const expiry15Match = code.match(/\(15\)(\d{6})/);
  if (expiry15Match && !result.expiryDate) {
    result.expiryDate = parseGS1Date(expiry15Match[1]);
    console.log('Found GS1 AI-15 best before:', result.expiryDate);
  }
  
  // GS1 AI 02 = GTIN-14
  const gtin14Match = code.match(/\(02\)(\d{14})/);
  if (gtin14Match) {
    result.ean = gtin14Match[1];
    console.log('Found GTIN-14:', result.ean);
  }
  
  // GS1 AI 01 = GTIN-12/13/14
  const gtin01Match = code.match(/\(01\)(\d{12,14})/);
  if (gtin01Match) {
    result.ean = gtin01Match[1];
    console.log('Found GTIN:', result.ean);
  }
  
  // GS1 AI 10 = Batch/Lot Code
  const batchMatch = code.match(/\(10\)([^\(\)]+)/);
  if (batchMatch) {
    result.batchCode = batchMatch[1];
    console.log('Found Batch Code:', result.batchCode);
  }
  
  // GS1 AI 21 = Serial Number
  const serialMatch = code.match(/\(21\)([^\(\)]+)/);
  if (serialMatch) {
    result.serialNumber = serialMatch[1];
    console.log('Found Serial Number:', result.serialNumber);
  }
  
  // If no GS1 format, try plain EAN-13/12
  if (!result.ean && /^\d{12,14}$/.test(code)) {
    result.ean = code;
    console.log('Found plain EAN:', result.ean);
  }
  
  // Try to extract YYMMDD from various positions (common in non-GS1 codes)
  const dateMatch = code.match(/\b(\d{2})(\d{2})(\d{2})\b/);
  if (dateMatch && !result.expiryDate) {
    const yy = parseInt(dateMatch[1]);
    const mm = parseInt(dateMatch[2]);
    const dd = parseInt(dateMatch[3]);
    
    // Validate it looks like a date
    if (mm >= 1 && mm <= 12 && dd >= 1 && dd <= 31) {
      const fullYear = yy > 50 ? 1900 + yy : 2000 + yy;
      result.expiryDate = `${fullYear}-${String(mm).padStart(2, '0')}-${String(dd).padStart(2, '0')}`;
      console.log('Found potential date:', result.expiryDate);
    }
  }
  
  return result;
}

/**
 * Parse GS1 date format (YYMMDD)
 */
function parseGS1Date(yymmdd) {
  const yy = parseInt(yymmdd.substring(0, 2));
  const mm = parseInt(yymmdd.substring(2, 4));
  const dd = parseInt(yymmdd.substring(4, 6));
  
  // GS1 spec: 00-49 = 2000-2049, 50-99 = 1950-1999
  const fullYear = yy <= 49 ? 2000 + yy : 1900 + yy;
  
  const dateStr = `${fullYear}-${String(mm).padStart(2, '0')}-${String(dd).padStart(2, '0')}`;
  console.log(`GS1 Date: ${yymmdd} -> ${dateStr}`);
  
  return dateStr;
}

/**
 * Check expiry date and show alerts
 */
function checkExpiryAlert(expiryDateStr) {
  try {
    const expiryDate = new Date(expiryDateStr);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    expiryDate.setHours(0, 0, 0, 0);
    
    const daysUntilExpiry = Math.ceil((expiryDate - today) / (1000 * 60 * 60 * 24));
    
    console.log('Days until expiry:', daysUntilExpiry);
    
    if (daysUntilExpiry < 0) {
      showError('🚨 EXPIRED! This product expired ' + Math.abs(daysUntilExpiry) + ' days ago.');
    } else if (daysUntilExpiry === 0) {
      showError('⚠️ EXPIRES TODAY! Use immediately.');
    } else if (daysUntilExpiry === 1) {
      showError('⚠️ Expires TOMORROW! Use soon.');
    } else if (daysUntilExpiry <= 3) {
      showError(`⚠️ CRITICAL: Expires in ${daysUntilExpiry} days!`);
    } else if (daysUntilExpiry <= 7) {
      showError(`⏱️ Warning: Expires in ${daysUntilExpiry} days`);
    } else if (daysUntilExpiry <= 30) {
      showSuccess(`📅 Expires in ${daysUntilExpiry} days`);
    }
  } catch (e) {
    console.error('Error checking expiry:', e);
  }
}

/**
 * Stop QR code scanner
 */
function stopQrScanner() {
  if (!scannerActive) return;
  
  try {
    // Stop scanning loop
    if (scanningInterval) {
      cancelAnimationFrame(scanningInterval);
      scanningInterval = null;
    }
    
    // Stop video stream and all tracks
    if (videoStream) {
      videoStream.getTracks().forEach(track => {
        track.stop();
      });
      videoStream = null;
    }
    
    // Clear scanner div
    const scannerDiv = document.getElementById('qr-scanner');
    if (scannerDiv) {
      scannerDiv.innerHTML = '';
    }
    
    scannerActive = false;
    console.log('✅ Scanner stopped');
  } catch (error) {
    console.error('Error stopping scanner:', error);
  }
}

/**
 * Fetch product information from backend using barcode/EAN
 */
async function fetchProductInfo(ean) {
  try {
    showLoading();
    
    const response = await fetch(`${getApiBaseUrl()}/tracker/product-info`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${getToken()}`
      },
      body: JSON.stringify({ ean: ean })
    });
    
    if (!response.ok) {
      console.log('Product not in database, allowing manual entry');
      populateQrForm(ean, 'Scanned Product', ean, null);
      return;
    }
    
    const data = await response.json();
    console.log('Product info retrieved:', data);
    
    populateQrForm(ean, data.product_name || data.name || 'Scanned Product', ean, null);
    showSuccess('✅ Product found! Please enter expiry date.');
    
  } catch (error) {
    console.error('Error fetching product info:', error);
    populateQrForm(ean, 'Scanned Product', ean, null);
  } finally {
    hideLoading();
  }
}

/**
 * Populate QR form with scanned data
 */
function populateQrForm(ean, productName, productCode, expiryDate = null) {
  const nameInput = document.getElementById('qr-product-name');
  const eanInput = document.getElementById('qr-product-ean');
  const expiryInput = document.getElementById('qr-expiry-date');
  const expiryForm = document.getElementById('qr-expiry-form');
  
  if (nameInput) nameInput.value = productName;
  if (eanInput) eanInput.value = productCode;
  
  // If expiry date was extracted from QR, pre-fill it
  if (expiryDate && expiryInput) {
    // Ensure the date is in YYYY-MM-DD format
    let formattedDate = expiryDate;
    
    // If it's already in YYYY-MM-DD format, use it as is
    if (/^\d{4}-\d{2}-\d{2}$/.test(expiryDate)) {
      formattedDate = expiryDate;
    } else if (/^\d{2}-\d{2}-\d{4}$/.test(expiryDate)) {
      // DD-MM-YYYY to YYYY-MM-DD
      const parts = expiryDate.split('-');
      formattedDate = `${parts[2]}-${parts[1]}-${parts[0]}`;
    } else if (/^\d{2}\/\d{2}\/\d{4}$/.test(expiryDate)) {
      // DD/MM/YYYY to YYYY-MM-DD
      const parts = expiryDate.split('/');
      formattedDate = `${parts[2]}-${parts[1]}-${parts[0]}`;
    }
    
    expiryInput.value = formattedDate;
    expiryInput.disabled = false; // Allow user to edit if needed
    console.log('✅ Pre-filled expiry date from QR:', formattedDate);
  } else if (expiryInput) {
    expiryInput.disabled = false;
  }
  
  if (expiryForm) {
    expiryForm.style.display = 'block';
    console.log('✅ QR Form displayed with extracted data');
  }
}

/**
 * Handle QR expiry form submission
 */
async function handleQrFormSubmit(event) {
  event.preventDefault();
  
  const productName = document.getElementById('qr-product-name').value;
  const productCode = document.getElementById('qr-product-ean').value;
  const expiryDate = document.getElementById('qr-expiry-date').value;
  const user = getCurrentUser();
  
  if (!user || !user.email) {
    showError('User not authenticated');
    return;
  }
  
  try {
    showLoading();
    
    // First, save the QR decoded data if we have it
    if (lastScannedQRData) {
      try {
        console.log('Saving QR decoded data to backend...', lastScannedQRData);
        
        const qrResponse = await fetch(`${getApiBaseUrl()}/tracker/qr-decoded-data`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${getToken()}`
          },
          body: JSON.stringify({
            ...lastScannedQRData,
            expiryDate: expiryDate || lastScannedQRData.expiryDate
          })
        });
        
        if (qrResponse.ok) {
          const qrData = await qrResponse.json();
          console.log('✅ QR data saved to backend:', qrData.qrDataId);
        } else {
          const qrError = await qrResponse.json();
          console.warn('⚠️ Failed to save QR data:', qrError);
          // Continue anyway, as the grocery item can still be saved
        }
      } catch (qrError) {
        console.warn('⚠️ Error saving QR data:', qrError);
        // Continue anyway, as the grocery item can still be saved
      }
    }
    
    // Then save the grocery item
    const response = await fetch(`${getApiBaseUrl()}/tracker/add-item`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${getToken()}`
      },
      body: JSON.stringify({
        userEmail: user.email,
        itemName: productName,
        expiryDate: expiryDate,
        productCode: productCode,
        scannedFromQR: true
      })
    });
    
    if (!response.ok) {
      const error = await response.json();
      showError(error.error || 'Failed to add item');
      return;
    }
    
    const data = await response.json();
    showSuccess('✅ Item added successfully! Expiry alert activated.');
    
    // Reset form and data
    document.getElementById('qr-expiry-form').reset();
    document.getElementById('qr-expiry-form').style.display = 'none';
    lastScannedQRData = null;
    
    // Reload tracker items
    if (typeof loadTrackerItems === 'function') {
      await loadTrackerItems();
    }
    
    // Switch back to manual tab
    switchTrackerTab('manual');
    
  } catch (error) {
    console.error('Error adding item:', error);
    showError('Error adding item: ' + error.message);
  } finally {
    hideLoading();
  }
}

/**
 * Initialize QR scanner on page load
 */
document.addEventListener('DOMContentLoaded', () => {
  const qrForm = document.getElementById('qr-expiry-form');
  if (qrForm) {
    qrForm.addEventListener('submit', handleQrFormSubmit);
  }
  
  addTrackerTabStyles();
  
  // Auto-start scanner if QR tab is visible (it's the default)
  setTimeout(() => {
    const qrContainer = document.getElementById('tracker-qr-form-container');
    if (qrContainer && qrContainer.style.display !== 'none') {
      startQrScanner();
    }
  }, 500);
});

/**
 * Add CSS styles for tracker tabs and scanner (Mobile Friendly)
 */
function addTrackerTabStyles() {
  if (document.getElementById('tracker-tab-styles')) return;
  
  const style = document.createElement('style');
  style.id = 'tracker-tab-styles';
  style.innerHTML = `
    .tracker-tab-btn {
      padding: 10px 20px;
      border-radius: 10px;
      background: rgba(138, 97, 255, 0.1);
      border: 1px solid rgba(138, 97, 255, 0.2);
      color: rgba(210, 220, 255, 0.7);
      cursor: pointer;
      font-weight: 600;
      font-size: 0.9rem;
      transition: all 200ms ease;
      touch-action: manipulation;
    }
    
    .tracker-tab-btn:hover {
      background: rgba(138, 97, 255, 0.15);
      border-color: rgba(138, 97, 255, 0.4);
    }
    
    .tracker-tab-btn.active {
      background: linear-gradient(135deg, #8257ff, #5f40ff);
      color: #ffffff;
      border-color: rgba(138, 97, 255, 0.6);
      box-shadow: 0 4px 16px rgba(130, 87, 255, 0.3);
    }
    
    #qr-scanner {
      background: #000 !important;
      border-radius: 12px;
      overflow: hidden;
      position: relative;
      display: flex;
      align-items: center;
      justify-content: center;
      width: 100%;
      height: 300px;
      min-height: 300px;
    }
    
    #qr-video {
      width: 100%;
      height: 100%;
      object-fit: cover;
    }
    
    /* Mobile responsive - make scanner full width */
    @media (max-width: 768px) {
      .tracker-tab-btn {
        padding: 8px 14px;
        font-size: 0.8rem;
        flex: 1;
      }
      
      #qr-scanner {
        height: 100%;
        min-height: 400px;
        aspect-ratio: 1 / 1.2;
      }
      
      #qr-video {
        width: 100%;
        height: 100%;
      }
    }
    
    @media (max-width: 480px) {
      #qr-scanner {
        min-height: 350px;
      }
    }
  `;
  document.head.appendChild(style);
}

/**
 * Clean up on page unload
 */
window.addEventListener('beforeunload', () => {
  stopQrScanner();
});

/**
 * Pause scanner if page/tab becomes hidden
 */
document.addEventListener('visibilitychange', () => {
  if (document.hidden) {
    stopQrScanner();
    console.log('Page hidden - scanner stopped');
  }
});

/**
 * Handle permission request UI hints
 */
console.log('QR Scanner ready. Permission will be requested when "Scan Me" tab is clicked.');
