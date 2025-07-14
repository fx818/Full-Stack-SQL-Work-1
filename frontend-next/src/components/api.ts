const API_BASE_URL = 'http://localhost:8001/api/v1';

export interface QuestionRequest {
  username: string;
  question: string;
}

export interface QueryResponse {
  question: string;
  resolved_question: string;
  query: string;
  result: string;
  answer: string;
  success: boolean;
  error?: string;
}

export interface ApprovalResponse {
  question: string;
  resolved_question: string;
  query: string;
  result: string | null;
  answer: string;
  success: boolean;
  error?: string;
  message: string;
  state_hex: string;
}

export interface QueryApprovalRequest {
  state_hex: string;
  feedback: string;
}

export interface MemoryCommandRequest {
  username: string;
  command: string;
}

export interface MemoryResponse {
  success: boolean;
  message: string;
  data?: unknown;
}

export interface HealthResponse {
  status: string;
  database_connected: boolean;
  supabase_connected: boolean;
  timestamp: string;
}

export interface UsersResponse {
  success: boolean;
  users: string[];
  total_users: number;
}

class ApiService {
  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`;
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return response.json();
  }

  // Query processing
  async sendQuery(request: QuestionRequest): Promise<QueryResponse | ApprovalResponse> {
    return this.request<QueryResponse | ApprovalResponse>('/query', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  async approveQuery(request: QueryApprovalRequest): Promise<QueryResponse> {
    return this.request<QueryResponse>('/query/approve', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  async regenerateQuery(request: QueryApprovalRequest): Promise<ApprovalResponse> {
    return this.request<ApprovalResponse>('/query/regenerate', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  // Memory commands
  async handleMemoryCommand(request: MemoryCommandRequest): Promise<MemoryResponse> {
    return this.request<MemoryResponse>('/memory/command', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  async getUserHistory(username: string): Promise<unknown> {
    return this.request(`/memory/${username}/history`);
  }

  async clearUserMemory(username: string): Promise<unknown> {
    return this.request(`/memory/${username}`, {
      method: 'DELETE',
    });
  }

  // System endpoints
  async checkHealth(): Promise<HealthResponse> {
    return this.request<HealthResponse>('/health');
  }

  async getAllUsers(): Promise<UsersResponse> {
    return this.request<UsersResponse>('/users');
  }

  async getDatabaseSchema(): Promise<unknown> {
    return this.request('/schema');
  }
}

export const apiService = new ApiService(); 