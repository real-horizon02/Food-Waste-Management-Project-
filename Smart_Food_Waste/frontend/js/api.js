/**
 * API communication functions
 */

// Use window.API_BASE_URL if set, otherwise default
// Don't declare as const to avoid conflicts - use a function to get it
function getApiBaseUrl() {
    if (typeof window !== 'undefined' && window.API_BASE_URL) {
        return window.API_BASE_URL;
    }
    return 'http://localhost:5000/api';
}

/**
 * Make API request with authentication
 */
async function apiRequest(endpoint, method = 'GET', data = null) {
    // Get token - ensure getToken function is available
    let token = null;
    if (typeof getToken === 'function') {
        token = getToken();
    } else if (typeof window !== 'undefined') {
        try {
            token = localStorage.getItem('access_token');
        } catch (e) {
            console.warn('Could not get token from localStorage', e);
        }
    }
    
    const headers = {
        'Content-Type': 'application/json'
    };
    
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    } else {
        console.warn('No authentication token found for request to', endpoint);
    }
    
    const options = {
        method,
        headers
    };
    
    if (data && (method === 'POST' || method === 'PUT')) {
        options.body = JSON.stringify(data);
    }
    
    try {
        const response = await fetch(`${getApiBaseUrl()}${endpoint}`, options);
        
        // Clone response for error handling
        const responseClone = response.clone();
        
        // Try to parse as JSON first
        let result;
        const contentType = response.headers.get('content-type') || '';
        
        if (contentType.includes('application/json')) {
            try {
                result = await response.json();
            } catch (jsonError) {
                // If JSON parsing fails, try text
                const text = await responseClone.text();
                throw new Error(text || `Server returned ${response.status} with invalid JSON`);
            }
        } else {
            // Non-JSON response
            const text = await response.text();
            if (!response.ok) {
                throw new Error(text || `Server returned ${response.status}`);
            }
            // Success with non-JSON - return text
            return { message: text };
        }
        
        // Check if response is OK
        if (!response.ok) {
            // Handle authentication errors gracefully
            if (response.status === 401 || response.status === 403) {
                const errorMsg = result.error || result.message || 'Authentication failed';
                console.error('Authentication error:', {
                    status: response.status,
                    endpoint: endpoint,
                    error: errorMsg,
                    hasToken: !!token
                });
                
                // Clear invalid token
                if (typeof removeToken === 'function') {
                    removeToken();
                }
                if (typeof removeCurrentUser === 'function') {
                    removeCurrentUser();
                }
                
                // Redirect to login if not already there
                if (!window.location.pathname.includes('login.html') && 
                    !window.location.pathname.includes('register.html')) {
                    if (typeof showAuth === 'function') {
                        showAuth();
                    } else {
                        // Fallback: redirect to login
                        setTimeout(() => {
                            window.location.href = 'login.html';
                        }, 2000);
                    }
                }
                
                throw new Error('Your session has expired. Please log in again.');
            }
            
            const errorMsg = result.error || result.message || `Request failed with status ${response.status}`;
            console.error('API Error:', {
                status: response.status,
                endpoint: endpoint,
                error: errorMsg,
                data: result
            });
            throw new Error(errorMsg);
        }
        
        return result;
    } catch (error) {
        // Network errors or fetch failures
        if (error.name === 'TypeError' && error.message.includes('fetch')) {
            throw new Error('Failed to connect to server. Make sure the backend is running on http://localhost:5000');
        }
        // If it's already an Error with a message, pass it through
        if (error instanceof Error) {
            throw error;
        }
        // Otherwise, wrap it
        throw new Error(`Network error: ${error.message || 'Unknown error occurred'}`);
    }
}

/**
 * Auth API calls
 */
const authAPI = {
    register: async (username, email, password, householdSize) => {
        const data = {
            username: username ? username.trim() : '',
            email: email ? email.trim().toLowerCase() : '',
            password: password || '',
            household_size: householdSize ? String(householdSize).trim() : '1'
        };
        
        console.log('authAPI.register - Sending data:', {
            ...data,
            password: '***' // Don't log password
        });
        
        return apiRequest('/auth/register', 'POST', data);
    },
    
    login: async (username, password) => {
        return apiRequest('/auth/login', 'POST', {
            username,
            password
        });
    },
    
    getCurrentUser: async () => {
        return apiRequest('/auth/me', 'GET');
    }
};

// Make authAPI globally available immediately
if (typeof window !== 'undefined') {
    window.authAPI = authAPI;
}

        /**
         * Dish API calls
         */
        const dishAPI = {
            search: async (dishName) => {
                try {
                    return await apiRequest('/dish/search', 'POST', {
                        dish_name: dishName
                    });
                } catch (error) {
                    // If search fails, try again with "recipe" appended
                    console.log('Initial search failed, trying with "recipe" suffix...');
                    try {
                        return await apiRequest('/dish/search', 'POST', {
                            dish_name: `${dishName} recipe`
                        });
                    } catch (retryError) {
                        // If still fails, throw original error
                        throw error;
                    }
                }
            },
    
    extractFromUrl: async (recipeUrl) => {
        return apiRequest('/dish/extract-url', 'POST', {
            recipe_url: recipeUrl
        });
    },
    
    getFavorites: async () => {
        return apiRequest('/dish/favorites', 'GET');
    },
    
    addFavorite: async (dishName) => {
        return apiRequest('/dish/favorites', 'POST', {
            dish_name: dishName
        });
    },
    
    downloadRecipePDF: async (recipeId) => {
        return apiRequest(`/dish/recipe/${recipeId}/download/pdf`, 'GET');
    },
    
    downloadIngredientsPDF: async (recipeId) => {
        return apiRequest(`/dish/ingredients/${recipeId}/download/pdf`, 'GET');
    }
};

// Make dishAPI globally available
if (typeof window !== 'undefined') {
    window.dishAPI = dishAPI;
}

/**
 * Grocery API calls
 */
const groceryAPI = {
    generate: async (dishName, householdSize, recipeId) => {
        return apiRequest('/grocery/generate', 'POST', {
            dish_name: dishName,
            household_size: householdSize,
            recipe_id: recipeId
        });
    },
    
    getLists: async () => {
        return apiRequest('/grocery/lists', 'GET');
    },
    
    getList: async (listId) => {
        return apiRequest(`/grocery/lists/${listId}`, 'GET');
    },
    
    updateList: async (listId, data) => {
        return apiRequest(`/grocery/lists/${listId}`, 'PUT', data);
    },
    
    deleteList: async (listId) => {
        return apiRequest(`/grocery/lists/${listId}`, 'DELETE');
    },
    
    downloadPDF: async (listId) => {
        return apiRequest(`/grocery/lists/${listId}/download/pdf`, 'GET');
    },
    
    downloadCSV: async (listId) => {
        return apiRequest(`/grocery/lists/${listId}/download/csv`, 'GET');
    }
};

/**
 * User API calls
 */
const userAPI = {
    getProfile: async () => {
        return apiRequest('/user/profile', 'GET');
    },
    
    updateProfile: async (data) => {
        return apiRequest('/user/profile', 'PUT', data);
    }
};

// ------------------- PDF / Text extraction APIs -------------------
// Add PDF extraction methods to dishAPI
dishAPI.extractFromPdf = async (file) => {
    // file is a File object
    const form = new FormData();
    form.append('file', file, file.name);
    const token = getToken();
    const headers = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;

    try {
        const resp = await fetch(`${getApiBaseUrl()}/dish/extract-pdf`, {
            method: 'POST',
            headers,
            body: form
        });
        if (!resp.ok) {
            const t = await resp.text();
            throw new Error(t || `Server returned ${resp.status}`);
        }
        const json = await resp.json();
        return json;
    } catch (err) {
        throw err;
    }
};

// Send pre-extracted text to backend
dishAPI.extractFromText = async (text) => {
    return apiRequest('/dish/extract-text', 'POST', { text });
};

// Make all API objects globally available
if (typeof window !== 'undefined') {
    window.dishAPI = dishAPI;
    window.groceryAPI = groceryAPI;
    window.userAPI = userAPI;
    window.authAPI = authAPI;
}
