import axios from "axios";
import { toast } from "sonner";

// Retrieve the base URL from env or fallback to local fastapi server
const baseURL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export const apiClient = axios.create({
  baseURL,
  withCredentials: true, // Crucial for sending and receiving the HttpOnly session cookie
  headers: {
    "Accept": "application/json",
    "Content-Type": "application/json",
  },
});

// Request interceptor to automatically attach authorization header
apiClient.interceptors.request.use(
  (config) => {
    const accessToken = localStorage.getItem("access_token");
    if (accessToken) {
      config.headers["Authorization"] = `Bearer ${accessToken}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Flag to track token refresh status
let isRefreshing = false;
let failedQueue: any[] = [];

// Helper to process queued requests after token refresh completes/fails
const processQueue = (error: any, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

// Response interceptor to manage global error conditions and automatic token refresh
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    const status = error.response?.status;

    // Try to refresh token on 401 errors, if we haven't already retried this request
    if (status === 401 && originalRequest && !originalRequest._retry) {
      const refreshToken = localStorage.getItem("refresh_token");
      
      if (refreshToken) {
        if (isRefreshing) {
          // Queue the request if a refresh is already in progress
          return new Promise((resolve, reject) => {
            failedQueue.push({ resolve, reject });
          })
            .then((token) => {
              originalRequest.headers["Authorization"] = `Bearer ${token}`;
              return apiClient(originalRequest);
            })
            .catch((err) => Promise.reject(err));
        }

        originalRequest._retry = true;
        isRefreshing = true;

        try {
          // Call refresh endpoint directly using basic axios to bypass interceptor logic
          const response = await axios.post(
            `${baseURL}/auth/refresh`,
            {},
            {
              headers: {
                "Authorization": `Bearer ${refreshToken}`,
              },
            }
          );

          const { access_token } = response.data;
          localStorage.setItem("access_token", access_token);
          
          apiClient.defaults.headers.common["Authorization"] = `Bearer ${access_token}`;
          originalRequest.headers["Authorization"] = `Bearer ${access_token}`;
          
          processQueue(null, access_token);
          isRefreshing = false;
          
          return apiClient(originalRequest);
        } catch (refreshError) {
          processQueue(refreshError, null);
          isRefreshing = false;
          
          // Clear credentials since refresh failed
          localStorage.removeItem("access_token");
          localStorage.removeItem("refresh_token");
          
          if (typeof window !== "undefined" && window.location.pathname.startsWith("/app")) {
            toast.error("Session expired. Please log in again.");
            window.location.href = "/";
          }
          return Promise.reject(refreshError);
        }
      } else {
        // No refresh token available, clear access token and redirect
        localStorage.removeItem("access_token");
        if (typeof window !== "undefined" && window.location.pathname.startsWith("/app")) {
          toast.error("Session expired. Please log in again.");
          window.location.href = "/";
        }
      }
    }

    // Extract structured error message from FastAPI backend
    let message = "An unexpected error occurred.";
    if (error.response?.data) {
      const data = error.response.data;
      if (data.errors && data.errors.length > 0) {
        message = data.errors[0].message;
      } else if (data.detail) {
        message = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
      }
    } else if (error.message) {
      message = error.message;
    }

    if (status === 402) {
      // Payment Required: display persistent subscription warning and redirect
      if (typeof window !== "undefined") {
        toast.error("Subscription expired. Please choose a plan to restore access.", {
          duration: 10000,
        });
        window.location.href = "/#pricing";
      }
    } else if (status !== 401) {
      // General error toaster (skip 401s as they are handled by auth/redirects above)
      toast.error(message);
    }

    return Promise.reject(error);
  }
);
