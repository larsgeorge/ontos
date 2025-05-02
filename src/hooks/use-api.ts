import { useState, useCallback } from 'react';

interface ApiResponse<T> {
  data: T;
  error?: string | null;
}

export const useApi = () => {
  const [loading, setLoading] = useState(false);

  // Use useCallback to ensure function identity is preserved across renders
  const get = useCallback(async <T>(url: string): Promise<ApiResponse<T>> => {
    setLoading(true);
    try {
      const response = await fetch(url);
      const data = await response.json();
      return { data };
    } catch (error) {
      console.error(`[useApi] GET error from ${url}:`, error);
      return { data: {} as T, error: (error as Error).message };
    } finally {
      setLoading(false);
    }
  }, []);

  const post = useCallback(async <T>(url: string, body: any): Promise<ApiResponse<T>> => {
    setLoading(true);
    try {
      let headers: Record<string, string> = {};
      let requestBody: BodyInit;

      if (body instanceof FormData) {
        // Don't set Content-Type for FormData, browser does it with boundary
        requestBody = body;
      } else {
        // Default to JSON
        headers['Content-Type'] = 'application/json';
        requestBody = JSON.stringify(body);
      }

      const response = await fetch(url, {
        method: 'POST',
        headers: headers, // Use dynamically set headers
        body: requestBody, // Use dynamically set body
      });
      
      // --- Primary Check: Response Status --- 
      if (!response.ok) {
          let errorBody: any;
          const contentType = response.headers.get('Content-Type');
          try {
              if (contentType?.includes('application/json')) {
                  errorBody = await response.json();
              } else {
                  errorBody = await response.text();
              }
          } catch (parseError) {
              // If parsing fails, use status text
              errorBody = response.statusText;
          }

          // Extract meaningful error message (FastAPI detail format or fallback)
          const errorMsg = errorBody?.detail?.[0]?.msg || // FastAPI validation detail
                           errorBody?.detail ||             // FastAPI simple detail string
                           (typeof errorBody === 'string' ? errorBody : JSON.stringify(errorBody)) || // Raw body or stringified obj
                           `HTTP error! status: ${response.status}`;         // Fallback

          console.error(`[useApi] POST error response from ${url} (${response.status}):`, errorBody);
          return { data: {} as T, error: errorMsg };
      }

      // --- Handle Successful Response (response.ok is true) --- 
      let data: any;
      try {
           // Handle potential empty response body for 2xx status codes
          if (response.headers.get('Content-Length') === '0' || response.status === 204) {
            data = {} as T; // Return empty object for success with no content
          } else if (response.headers.get('Content-Type')?.includes('application/json')){
             data = await response.json();
          } else {
             data = await response.text(); // Handle non-JSON success response
          }
          console.log(`[useApi] POST successful response from ${url}:`, data);
          return { data: data as T };
          
      } catch (parseError) {
           console.error(`[useApi] Error parsing successful response from ${url}:`, parseError);
           return { data: {} as T, error: `Failed to parse response: ${(parseError as Error).message}` };
      }
      
    } catch (error) {
      // Network errors or errors before fetch response
      console.error(`[useApi] Network or other error during POST to ${url}:`, error);
      return { data: {} as T, error: (error as Error).message };
    } finally {
      setLoading(false);
    }
  }, []);

  const put = useCallback(async <T>(url: string, body: any): Promise<ApiResponse<T>> => {
    console.log(`[useApi] PUT request to ${url}`, body);
    setLoading(true);
    try {
      const response = await fetch(url, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
      });
      const data = await response.json();
      console.log(`[useApi] PUT response from ${url}:`, data);
      return { data };
    } catch (error) {
      console.error(`[useApi] PUT error from ${url}:`, error);
      return { data: {} as T, error: (error as Error).message };
    } finally {
      setLoading(false);
    }
  }, []);

  const delete_ = useCallback(async (url: string): Promise<ApiResponse<unknown>> => {
    console.log(`[useApi] DELETE request to ${url}`);
    setLoading(true);
    let responseData: unknown = null;
    let errorMsg: string | null = null;
    try {
      const response = await fetch(url, { method: 'DELETE' });

      // Check status and potentially parse error body
      if (!response.ok) {
          let errorBody: any;
          const contentType = response.headers.get('Content-Type');
          try {
              if (contentType?.includes('application/json')) {
                  errorBody = await response.json();
              } else {
                  errorBody = await response.text();
              }
          } catch (parseError) {
              errorBody = response.statusText; // Fallback
          }
          errorMsg = errorBody?.detail || (typeof errorBody === 'string' ? errorBody : JSON.stringify(errorBody)) || `HTTP error! status: ${response.status}`;
          console.error(`[useApi] DELETE error response from ${url} (${response.status}):`, errorBody);
      } else {
          // Success (usually 204 No Content for DELETE)
          console.log(`[useApi] DELETE successful for ${url} (status: ${response.status})`);
          // No data expected for successful delete, but structure requires data field
          responseData = {}; 
      }

    } catch (error) {
      // Network errors
      errorMsg = (error as Error).message;
      console.error(`[useApi] Network or other error during DELETE to ${url}:`, error);
    } finally {
      setLoading(false);
    }
    return { data: responseData, error: errorMsg };
  }, []);

  return { get, post, put, delete: delete_, loading };
};